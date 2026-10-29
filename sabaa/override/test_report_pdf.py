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


def make_pdf() -> bytes:
	# File validates the PDF content, so the job needs a real PDF.
	writer = PdfWriter()
	writer.add_blank_page(width=100, height=100)
	output = BytesIO()
	writer.write(output)
	return output.getvalue()


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


class TestReportToPdf(FrappeTestCase):
	def setUp(self):
		frappe.local.response = frappe._dict()
		access_log = patch(f"{MODULE}.make_access_log")
		access_log.start()
		self.addCleanup(access_log.stop)

	@patch(f"{MODULE}.get_pdf", return_value=b"%PDF")
	@patch(f"{MODULE}.frappe.enqueue")
	def test_small_report_renders_synchronously(self, enqueue, get_pdf):
		with patch.dict(frappe.conf, {"report_pdf_background_row_threshold": 1000}):
			result = report_pdf.report_to_pdf(make_report_html(250))

		self.assertIsNone(result)
		enqueue.assert_not_called()
		self.assertEqual(frappe.local.response.type, "pdf")
		self.assertEqual(frappe.local.response.filecontent, b"%PDF")
		self.assertEqual(get_pdf.call_args.args[0].count("<thead>"), 3)

	@patch(f"{MODULE}.get_pdf")
	@patch(f"{MODULE}.frappe.enqueue")
	def test_large_report_is_queued(self, enqueue, get_pdf):
		with patch.dict(frappe.conf, {"report_pdf_background_row_threshold": 100}):
			result = report_pdf.report_to_pdf(make_report_html(250), orientation="Portrait")

		self.assertEqual(result["queued"], 1)
		get_pdf.assert_not_called()
		self.assertEqual(enqueue.call_args.kwargs["queue"], "long")
		self.assertEqual(enqueue.call_args.kwargs["orientation"], "Portrait")
		self.assertEqual(enqueue.call_args.kwargs["user"], frappe.session.user)
		self.assertEqual(enqueue.call_args.kwargs["token"], result["token"])
		self.assertEqual(report_pdf.get_report_pdf_status(result["token"])["status"], "Queued")


class TestGetReportPdfStatus(FrappeTestCase):
	def test_hides_status_from_other_users(self):
		report_pdf.set_pdf_status("token-other", "Administrator", "Ready", "/private/files/report.pdf")
		self.addCleanup(frappe.cache.delete_value, report_pdf.get_pdf_status_key("token-other"))

		with self.set_user("Guest"):
			self.assertEqual(report_pdf.get_report_pdf_status("token-other"), {"status": "Expired"})

	def test_unknown_token_is_expired(self):
		self.assertEqual(report_pdf.get_report_pdf_status("missing-token"), {"status": "Expired"})


class TestGetReportPdf(FrappeTestCase):
	def test_renders_many_pages_with_header_under_default_open_file_limit(self):
		# Supervisor starts workers with a soft limit of 1024 open files. wkhtmltopdf
		# opens the header and footer once per page, so a long report used to fail.
		soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
		resource.setrlimit(resource.RLIMIT_NOFILE, (1024, hard))
		self.addCleanup(resource.setrlimit, resource.RLIMIT_NOFILE, (soft, hard))
		pages = "".join(f'<div style="page-break-after: always">{i}</div>' for i in range(550))
		html = (
			'<html><head></head><body><div id="header-html">Letter Head</div>'
			f'<div id="footer-html">Footer</div>{pages}</body></html>'
		)

		pdf = report_pdf.get_report_pdf(html, "Portrait")

		self.assertGreaterEqual(len(PdfReader(BytesIO(pdf)).pages), 550)
		self.assertEqual(resource.getrlimit(resource.RLIMIT_NOFILE), (1024, hard))


class TestGenerateReportPdf(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_generate_report_pdf"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))
		self.user = frappe.session.user

	def get_last_notification(self):
		return frappe.get_last_doc("Notification Log", filters={"for_user": self.user})

	def start_job(self, token: str):
		report_pdf.set_pdf_status(token, self.user, "Queued")
		self.addCleanup(frappe.cache.delete_value, report_pdf.get_pdf_status_key(token))

	@patch(f"{MODULE}.get_pdf")
	def test_saves_private_file_and_marks_ready_after_commit(self, get_pdf):
		get_pdf.return_value = make_pdf()
		self.start_job("token-ready")
		report_pdf.generate_report_pdf("<html></html>", "Landscape", self.user, "token-ready")

		notification = self.get_last_notification()
		file = frappe.get_doc("File", {"file_url": notification.link})
		# The file is also on disk, which the savepoint rollback does not remove.
		self.addCleanup(file.delete, ignore_permissions=True)

		self.assertTrue(file.is_private)
		self.assertTrue(file.file_url.endswith(".pdf"))
		self.assertEqual(file.get_content(), get_pdf.return_value)
		self.assertEqual(report_pdf.get_report_pdf_status("token-ready")["status"], "Queued")

		frappe.db.after_commit.run()
		self.assertEqual(
			report_pdf.get_report_pdf_status("token-ready"),
			{"status": "Ready", "file_url": file.file_url},
		)

	@patch(f"{MODULE}.get_pdf", side_effect=OSError("wkhtmltopdf failed"))
	def test_marks_failed_and_raises_on_failure(self, get_pdf):
		self.start_job("token-failed")
		with self.assertRaises(OSError):
			report_pdf.generate_report_pdf("<html></html>", "Landscape", self.user, "token-failed")

		notification = self.get_last_notification()
		self.assertFalse(notification.link)
		self.assertIn("could not be generated", notification.subject)
		self.assertEqual(report_pdf.get_report_pdf_status("token-failed")["status"], "Failed")
