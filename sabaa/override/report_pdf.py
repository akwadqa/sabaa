import math
import os
import re
from urllib.parse import urlparse

import frappe
from bs4 import BeautifulSoup, Comment
from frappe import _
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.utils import now_datetime
from frappe.utils.pdf import get_file_data_from_writer, get_pdf
from pypdf import PdfWriter

ROWS_PER_TABLE = 100
# Each wkhtmltopdf run gets at most this many rows. One run keeps every page in memory and
# opens the header and footer once per page, so a full Accounts Receivable (5,748 rows,
# 588 pages) took 2.2 GB and hit the 1024 open files limit of the workers. 1,000 rows with
# a letter head are about 100 pages and 0.4 GB.
ROWS_PER_PDF_CHUNK = 1000
# Inline renders block the only gunicorn worker; 1,000 rows take about 15 seconds.
DEFAULT_BACKGROUND_ROW_THRESHOLD = 1000
# A chunk renders in about 15 seconds, so 60 seconds per chunk leaves room for a busy server.
PDF_JOB_SECONDS_PER_CHUNK = 60
MIN_PDF_JOB_TIMEOUT = 600
# Covers the time in the queue and the job, so a desk tab that polls late still gets the result.
PDF_STATUS_EXPIRY = 6 * 60 * 60

TBODY_PATTERN = re.compile(r"(<tbody[^>]*>)(.*?)</tbody>", re.S | re.I)
ROW_START_PATTERN = re.compile(r"(?=<tr[\s>])", re.I)
KEPT_IN_EVERY_DOCUMENT = ("header-html", "footer-html")
TABLE_MARKER = "sabaa-pdf-table"


@frappe.whitelist()
def report_to_pdf(html: str, orientation: str = "Landscape"):
	"""Override of `frappe.utils.print_format.report_to_pdf` for large reports.

	Prints that are too large to render during a web request go to a background job.
	"""
	make_access_log(file_type="PDF", method="PDF", page=html)
	row_count = count_rows(html)

	if row_count > get_background_row_threshold():
		token = frappe.generate_hash()
		timeout = get_pdf_job_timeout(row_count)
		set_pdf_status(token, frappe.session.user, "Queued")
		frappe.enqueue(
			generate_report_pdf,
			queue="long",
			timeout=timeout,
			html=html,
			orientation=orientation,
			user=frappe.session.user,
			token=token,
		)
		return {"queued": 1, "token": token, "timeout": timeout}

	frappe.local.response.filename = "report.pdf"
	frappe.local.response.filecontent = get_report_pdf(html, orientation)
	frappe.local.response.type = "pdf"


def get_report_pdf(html: str, orientation: str) -> bytes:
	"""Render the report with one wkhtmltopdf run per chunk of rows and merge the pages."""
	writer = PdfWriter()
	for document in split_into_documents(html):
		options = get_report_pdf_options(orientation)
		if writer.pages:
			options["page-offset"] = len(writer.pages)

		# wkhtmltopdf is very slow on one huge table, so long tables are split as well.
		get_pdf(split_large_tables(document), options, output=writer)

	return get_file_data_from_writer(writer)


def split_into_documents(html: str, rows_per_chunk: int | None = None) -> list[str]:
	"""Split the report into documents with at most `rows_per_chunk` rows of its main table.

	The content before the main table (title, filters) stays in the first document and the
	content after it in the last one. The letter head, footer and styles are in every document.
	"""
	rows_per_chunk = rows_per_chunk or ROWS_PER_PDF_CHUNK
	if count_rows(html) <= rows_per_chunk:
		return [html]

	tbody = get_main_table_body(html)
	if not tbody:
		return [html]

	leading, *rows = ROW_START_PATTERN.split(tbody.group(2))
	table_start = html.rfind("<table", 0, tbody.start())
	table_end = html.find("</table>", tbody.end())
	if len(rows) <= rows_per_chunk or table_start == -1 or table_end == -1:
		return [html]

	table_end += len("</table>")
	table_open = html[table_start : tbody.start(2)] + leading
	table_close = html[tbody.end(2) : table_end]

	# Only the document around the table is parsed, which is fast; the rows stay as text.
	soup = BeautifulSoup(f"{html[:table_start]}<!--{TABLE_MARKER}-->{html[table_end:]}", "html.parser")
	table = soup.find(string=lambda text: isinstance(text, Comment) and text == TABLE_MARKER)
	intro = extract_nodes([node for node in reversed(list(table.previous_siblings)) if not is_kept(node)])
	outro = extract_nodes([node for node in table.next_siblings if not is_kept(node)])
	remove_page_total(soup)
	template = str(soup)

	starts = range(0, len(rows), rows_per_chunk)
	return [
		template.replace(
			f"<!--{TABLE_MARKER}-->",
			(intro if start == 0 else "")
			+ table_open
			+ "".join(rows[start : start + rows_per_chunk])
			+ table_close
			+ (outro if start == starts[-1] else ""),
		)
		for start in starts
	]


def get_main_table_body(html: str) -> re.Match | None:
	"""The table body with the most rows, without nested tables."""
	bodies = [match for match in TBODY_PATTERN.finditer(html) if "<table" not in match.group(2).lower()]
	return max(bodies, key=lambda match: count_rows(match.group(2)), default=None)


def is_kept(node) -> bool:
	return getattr(node, "name", None) == "style" or (
		hasattr(node, "get") and node.get("id") in KEPT_IN_EVERY_DOCUMENT
	)


def extract_nodes(nodes: list) -> str:
	html = "".join(str(node) for node in nodes)
	for node in nodes:
		node.extract()
	return html


def remove_page_total(soup: BeautifulSoup):
	"""Each wkhtmltopdf run only knows its own page count, so "of N" would be wrong."""
	page_number = soup.select_one("#footer-html .page-number")
	if page_number:
		page_number.clear()
		page_number.append(BeautifulSoup(_("Page {0}").format('<span class="page"></span>'), "html.parser"))


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


def get_pdf_job_timeout(row_count: int) -> int:
	chunks = math.ceil(row_count / ROWS_PER_PDF_CHUNK)
	return max(MIN_PDF_JOB_TIMEOUT, chunks * PDF_JOB_SECONDS_PER_CHUNK)


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
	# rq runs each job in its own forked process, so this only lowers the priority of this
	# job and its wkhtmltopdf runs, which keeps web requests responsive.
	os.nice(10)
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
