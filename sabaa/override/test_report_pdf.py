import re
import resource
from io import BytesIO
from unittest.mock import patch

import frappe
from pypdf import PdfReader, PdfWriter
from frappe.tests.utils import FrappeTestCase

from sabaa.override import report_pdf

MODULE = "sabaa.override.report_pdf"


def make_report_html(row_count: int, row_html: str = "<td>Row {i}</td>") -> str:
	rows = "".join(f"<tr>{row_html.format(i=i)}</tr>" for i in range(row_count))
	return (
		"<html><body><h2>Accounts Receivable</h2>"
		'<table class="table"><thead><tr><th>Party</th></tr></thead>'
		f"<tbody>{rows}</tbody></table><p>Printed on today</p></body></html>"
	)


def make_printed_report_html(row_count: int, row_html: str = "<td>Row {i}</td>") -> str:
	"""Same structure as frappe's print_template.html with a letter head."""
	rows = "".join(f"<tr>{row_html.format(i=i)}</tr>" for i in range(row_count))
	return (
		"<html><head><style>.print-format { font-size: 8pt; }</style></head><body>"
		'<div class="print-format-gutter"><div id="footer-html" class="visible-pdf">'
		'<p class="text-center small page-number visible-pdf">'
		'Page <span class="page"></span> of <span class="topage"></span></p></div>'
		'<div class="print-format landscape">'
		'<div id="header-html" class="hidden-pdf"><div class="letter-head">Letter Head</div></div>'
		"<style>.print-format td { vertical-align: middle; }</style>"
		"<h2>Accounts Receivable</h2>"
		'<table class="table"><thead><tr><th>Party</th></tr></thead>'
		f"<tbody>{rows}</tbody></table><p>Printed on today</p></div></div></body></html>"
	)


def make_pdf() -> bytes:
	# File validates the PDF content, so the job needs a real PDF.
	writer = PdfWriter()
	writer.add_blank_page(width=100, height=100)
	output = BytesIO()
	writer.write(output)
	return output.getvalue()


def add_blank_page(html: str, options: dict, output: PdfWriter) -> PdfWriter:
	output.add_blank_page(width=100, height=100)
	return output


class TestSplitLargeTables(FrappeTestCase):
	def test_splits_long_table_into_chunks_with_header(self):
		html = report_pdf.split_large_tables(make_report_html(250))

		self.assertEqual(html.count('<table class="table">'), 3)
		self.assertEqual(html.count("<th>Party</th>"), 3)
		self.assertEqual(html.count("</table>"), 3)
		self.assertEqual(report_pdf.count_rows(html), 250 + 3)

		row_positions = [html.index(f"<td>Row {i}</td>") for i in range(250)]
		self.assertEqual(row_positions, sorted(row_positions))
		self.assertIn("<p>Printed on today</p>", html)

	def test_keeps_short_table_unchanged(self):
		html = make_report_html(100)
		self.assertEqual(report_pdf.split_large_tables(html), html)

	def test_keeps_table_with_nested_table_unchanged(self):
		html = make_report_html(250, "<td><table><tr><td>{i}</td></tr></table></td>")
		self.assertEqual(report_pdf.split_large_tables(html), html)


class TestSplitIntoDocuments(FrappeTestCase):
	def test_keeps_small_report_as_one_document(self):
		html = make_printed_report_html(100)
		self.assertEqual(report_pdf.split_into_documents(html, rows_per_chunk=100), [html])

	def test_keeps_report_without_table_body_as_one_document(self):
		html = "<html><body>" + "<tr><td>Row</td></tr>" * 30 + "</body></html>"
		self.assertEqual(report_pdf.split_into_documents(html, rows_per_chunk=10), [html])

	def test_splits_rows_in_order_without_losing_any(self):
		documents = report_pdf.split_into_documents(make_printed_report_html(250), rows_per_chunk=100)

		self.assertEqual(len(documents), 3)
		rows = [row for document in documents for row in re.findall(r"<td>Row (\d+)</td>", document)]
		self.assertEqual(rows, [str(i) for i in range(250)])
		for document in documents:
			self.assertEqual(document.count("<th>Party</th>"), 1)

	def test_keeps_intro_in_first_and_outro_in_last_document(self):
		documents = report_pdf.split_into_documents(make_printed_report_html(250), rows_per_chunk=100)

		self.assertEqual([("<h2>Accounts Receivable</h2>" in document) for document in documents], [True, False, False])
		self.assertEqual([("Printed on today" in document) for document in documents], [False, False, True])

	def test_keeps_letter_head_footer_and_styles_in_every_document(self):
		documents = report_pdf.split_into_documents(make_printed_report_html(250), rows_per_chunk=100)

		for document in documents:
			self.assertIn('<div class="letter-head">Letter Head</div>', document)
			self.assertIn('id="footer-html"', document)
			self.assertIn(".print-format td { vertical-align: middle; }", document)
			# Each wkhtmltopdf run only knows its own page count.
			self.assertIn('<span class="page"></span>', document)
			self.assertNotIn("topage", document)


class TestReportToPdf(FrappeTestCase):
	def setUp(self):
		frappe.local.response = frappe._dict()
		access_log = patch(f"{MODULE}.make_access_log")
		access_log.start()
		self.addCleanup(access_log.stop)

	@patch(f"{MODULE}.get_pdf", side_effect=add_blank_page)
	@patch(f"{MODULE}.frappe.enqueue")
	def test_small_report_renders_synchronously(self, enqueue, get_pdf):
		result = report_pdf.report_to_pdf(make_report_html(250))

		self.assertIsNone(result)
		enqueue.assert_not_called()
		self.assertEqual(frappe.local.response.type, "pdf")
		self.assertEqual(len(PdfReader(BytesIO(frappe.local.response.filecontent)).pages), 1)
		self.assertEqual(get_pdf.call_args.args[0].count("<thead>"), 3)

	@patch(f"{MODULE}.get_pdf")
	@patch(f"{MODULE}.frappe.enqueue")
	def test_large_report_is_queued(self, enqueue, get_pdf):
		html = make_report_html(1001)
		result = report_pdf.report_to_pdf(html, orientation="Portrait")

		self.assertEqual(result["queued"], 1)
		get_pdf.assert_not_called()
		self.assertEqual(enqueue.call_args.kwargs["queue"], "long")
		self.assertEqual(enqueue.call_args.kwargs["html"], html)
		self.assertEqual(enqueue.call_args.kwargs["orientation"], "Portrait")
		self.assertEqual(enqueue.call_args.kwargs["user"], frappe.session.user)
		self.assertEqual(enqueue.call_args.kwargs["token"], result["token"])
		self.assertEqual(enqueue.call_args.kwargs["timeout"], result["timeout"])
		self.assertEqual(report_pdf.get_report_pdf_status(result["token"])["status"], "Queued")

	def test_job_timeout_grows_with_rows(self):
		self.assertEqual(report_pdf.get_pdf_job_timeout(1001), 600)
		self.assertEqual(report_pdf.get_pdf_job_timeout(5748), 600)
		self.assertEqual(report_pdf.get_pdf_job_timeout(50000), 3000)


class TestGetReportPdfStatus(FrappeTestCase):
	def test_hides_status_from_other_users(self):
		report_pdf.set_pdf_status("token-other", "Administrator", "Ready", "/private/files/report.pdf")
		self.addCleanup(frappe.cache.delete_value, report_pdf.get_pdf_status_key("token-other"))

		with self.set_user("Guest"):
			self.assertEqual(report_pdf.get_report_pdf_status("token-other"), {"status": "Expired"})

	def test_unknown_token_is_expired(self):
		self.assertEqual(report_pdf.get_report_pdf_status("missing-token"), {"status": "Expired"})


class TestGetReportPdf(FrappeTestCase):
	@patch(f"{MODULE}.get_pdf", side_effect=add_blank_page)
	def test_continues_page_numbers_across_documents(self, get_pdf):
		with patch(f"{MODULE}.ROWS_PER_PDF_CHUNK", 100):
			pdf = report_pdf.get_report_pdf(make_printed_report_html(250), "Landscape")

		self.assertEqual(len(PdfReader(BytesIO(pdf)).pages), 3)
		offsets = [call.args[1].get("page-offset") for call in get_pdf.call_args_list]
		self.assertEqual(offsets, [None, 1, 2])

	def test_renders_many_pages_with_letter_head_under_default_open_file_limit(self):
		# Supervisor starts workers with a soft limit of 1024 open files. wkhtmltopdf opens the
		# header and footer once per page, so one run of about 500 pages or more fails.
		soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
		resource.setrlimit(resource.RLIMIT_NOFILE, (1024, hard))
		self.addCleanup(resource.setrlimit, resource.RLIMIT_NOFILE, (soft, hard))
		html = make_printed_report_html(600, '<td style="height: 150mm">Row {i}</td>')

		with patch(f"{MODULE}.ROWS_PER_PDF_CHUNK", 200):
			pdf = report_pdf.get_report_pdf(html, "Portrait")

		pages = PdfReader(BytesIO(pdf)).pages
		self.assertGreaterEqual(len(pages), 600)
		first_page_of_second_document = next(
			page for page in pages if "Row 200" in page.extract_text()
		).extract_text()
		self.assertRegex(first_page_of_second_document, r"Page\s+201\b")


class TestGenerateReportPdf(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_generate_report_pdf"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))
		self.user = frappe.session.user

		nice = patch(f"{MODULE}.os.nice")
		self.nice = nice.start()
		self.addCleanup(nice.stop)

	def get_last_notification(self):
		return frappe.get_last_doc("Notification Log", filters={"for_user": self.user})

	def start_job(self, token: str):
		report_pdf.set_pdf_status(token, self.user, "Queued")
		self.addCleanup(frappe.cache.delete_value, report_pdf.get_pdf_status_key(token))

	@patch(f"{MODULE}.get_report_pdf")
	def test_saves_private_file_and_marks_ready_after_commit(self, get_report_pdf):
		get_report_pdf.return_value = make_pdf()
		self.start_job("token-ready")
		report_pdf.generate_report_pdf("<html></html>", "Landscape", self.user, "token-ready")

		notification = self.get_last_notification()
		file = frappe.get_doc("File", {"file_url": notification.link})
		# The file is also on disk, which the savepoint rollback does not remove.
		self.addCleanup(file.delete, ignore_permissions=True)

		self.nice.assert_called_once_with(10)
		self.assertTrue(file.is_private)
		self.assertTrue(file.file_url.endswith(".pdf"))
		self.assertEqual(file.get_content(), get_report_pdf.return_value)
		self.assertEqual(report_pdf.get_report_pdf_status("token-ready")["status"], "Queued")

		frappe.db.after_commit.run()
		self.assertEqual(
			report_pdf.get_report_pdf_status("token-ready"),
			{"status": "Ready", "file_url": file.file_url},
		)

	@patch(f"{MODULE}.get_report_pdf", side_effect=OSError("wkhtmltopdf failed"))
	def test_marks_failed_and_raises_on_failure(self, get_report_pdf):
		self.start_job("token-failed")
		with self.assertRaises(OSError):
			report_pdf.generate_report_pdf("<html></html>", "Landscape", self.user, "token-failed")

		notification = self.get_last_notification()
		self.assertFalse(notification.link)
		self.assertIn("could not be generated", notification.subject)
		self.assertEqual(report_pdf.get_report_pdf_status("token-failed")["status"], "Failed")
