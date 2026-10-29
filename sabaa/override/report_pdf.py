import re
import resource
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils import now_datetime
from frappe.utils.pdf import get_pdf

ROWS_PER_TABLE = 100
# A letter head is rendered on every page; with it, 5,748 rows took about 112s
# against the 120s web timeout, while 4,000 rows stay well under it.
DEFAULT_BACKGROUND_ROW_THRESHOLD = 4000
# Two open files per page (header and footer) leaves room for about 30,000 pages.
OPEN_FILE_LIMIT = 65536
PDF_JOB_TIMEOUT = 1800
# Kept a while after the job ends, so a desk tab that polls late still gets the result.
PDF_STATUS_EXPIRY = 2 * PDF_JOB_TIMEOUT

TBODY_PATTERN = re.compile(r"(<tbody[^>]*>)(.*?)</tbody>", re.S | re.I)
ROW_START_PATTERN = re.compile(r"(?=<tr[\s>])", re.I)


@frappe.whitelist()
def report_to_pdf(html: str, orientation: str = "Landscape"):
	"""Override of `frappe.utils.print_format.report_to_pdf` for large reports.

	wkhtmltopdf is very slow on one huge table, so big tables are split first.
	Prints that are still too large for the web request timeout go to a background job.
	"""
	make_access_log(file_type="PDF", method="PDF", page=html)
	is_large = count_rows(html) > get_background_row_threshold()
	html = split_large_tables(html)

	if is_large:
		token = frappe.generate_hash()
		set_pdf_status(token, frappe.session.user, "Queued")
		frappe.enqueue(
			generate_report_pdf,
			queue="long",
			timeout=PDF_JOB_TIMEOUT,
			html=html,
			orientation=orientation,
			user=frappe.session.user,
			token=token,
		)
		return {"queued": 1, "token": token}

	frappe.local.response.filename = "report.pdf"
	frappe.local.response.filecontent = get_report_pdf(html, orientation)
	frappe.local.response.type = "pdf"


def get_report_pdf(html: str, orientation: str) -> bytes:
	"""Render with a raised open file limit, which the wkhtmltopdf child process inherits.

	With a letter head, wkhtmltopdf opens the header and footer HTML once per page. Supervisor
	starts workers with a soft limit of 1024, so after about 500 pages wkhtmltopdf fails with
	"ContentAccessDenied". The hard limit is much higher and can be used without root.
	"""
	soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
	target = OPEN_FILE_LIMIT if hard == resource.RLIM_INFINITY else min(hard, OPEN_FILE_LIMIT)
	if soft >= target:
		return get_pdf(html, get_report_pdf_options(orientation))

	resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
	try:
		return get_pdf(html, get_report_pdf_options(orientation))
	finally:
		resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))


def split_large_tables(html: str, rows_per_table: int = ROWS_PER_TABLE) -> str:
	"""Close and reopen (with the same header) every table body longer than `rows_per_table`."""
	parts = []
	position = 0

	for match in TBODY_PATTERN.finditer(html):
		tbody_open, body = match.group(1), match.group(2)
		table_start = html.rfind("<table", 0, match.start())
		table_header = html[table_start : match.start()] + tbody_open
		rows = ROW_START_PATTERN.split(body)
		leading, rows = rows[0], rows[1:]

		is_splittable = (
			table_start != -1
			and len(rows) > rows_per_table
			and "<table" not in body.lower()
			and "</table>" not in table_header.lower()
		)
		if not is_splittable:
			continue

		chunks = ["".join(rows[i : i + rows_per_table]) for i in range(0, len(rows), rows_per_table)]
		parts.append(html[position : match.start()])
		parts.append(tbody_open + leading + ("</tbody></table>" + table_header).join(chunks) + "</tbody>")
		position = match.end()

	parts.append(html[position:])
	return "".join(parts)


def count_rows(html: str) -> int:
	return len(ROW_START_PATTERN.findall(html))


def get_background_row_threshold() -> int:
	return int(frappe.conf.get("report_pdf_background_row_threshold") or DEFAULT_BACKGROUND_ROW_THRESHOLD)


def get_report_pdf_options(orientation: str) -> dict:
	# Same options as core report_to_pdf.
	return {
		"orientation": orientation,
		"proxy": "http://0.0.0.0:0",
		"bypass-proxy-for": urlparse(frappe.utils.get_url(allow_header_override=False)).hostname,
		"load-error-handling": "ignore",
	}


@frappe.whitelist(methods=["GET"])
def get_report_pdf_status(token: str) -> dict:
	"""Polled by the desk while a queued report PDF renders.

	Socket.io is not available on this bench, so the desk polls. This reads one small
	Redis key and does not touch the database or the RQ job, which holds the full HTML.
	"""
	status = frappe.cache.get_value(get_pdf_status_key(token), expires=True)
	if not status or status["user"] != frappe.session.user:
		return {"status": "Expired"}

	return {"status": status["status"], "file_url": status.get("file_url")}


def set_pdf_status(token: str, user: str, status: str, file_url: str | None = None):
	frappe.cache.set_value(
		get_pdf_status_key(token),
		{"user": user, "status": status, "file_url": file_url},
		expires_in_sec=PDF_STATUS_EXPIRY,
	)


def get_pdf_status_key(token: str) -> str:
	return f"sabaa:report_pdf_status:{token}"


def generate_report_pdf(html: str, orientation: str, user: str, token: str):
	"""Background job: render the PDF, save it as a private file and notify the user."""
	try:
		pdf = get_report_pdf(html, orientation)
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"report-{now_datetime().strftime('%Y%m%d-%H%M%S')}.pdf",
				"is_private": 1,
				"content": pdf,
			}
		).insert(ignore_permissions=True)
	except Exception:
		set_pdf_status(token, user, "Failed")
		notify_user(user, _("The report PDF could not be generated. Please contact your administrator."))
		raise

	notify_user(user, _("Your report PDF is ready."), file.file_url)
	# The desk downloads the file as soon as it sees "Ready", so the File must be committed first.
	frappe.db.after_commit.add(lambda: set_pdf_status(token, user, "Ready", file.file_url))


def notify_user(user: str, message: str, file_url: str | None = None):
	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"type": "Alert",
			"subject": message,
			"link": file_url,
		}
	).insert(ignore_permissions=True)
