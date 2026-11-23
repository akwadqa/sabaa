# Copyright (c) 2026, Akwad Programming and Contributors
# See license.txt

import frappe
from frappe.utils import get_url
from van_sales.van_sales.api.print import get_document_html

from sabaa.sabaa.invoice_stamp.test_invoice_stamp import (
	NO_STAMP_GROUP,
	SABA_URL,
	SETTINGS,
	STAMP_GROUP,
	StampSetupTestCase,
)

PRINT_FORMAT = "Sales Invoice - Custom"


class TestInvoiceStampPrint(StampSetupTestCase):
	def test_print_shows_stamp_in_signature_box(self):
		html = self.render(self.submitted_invoice(group=STAMP_GROUP))

		self.assertIn('class="sign-stamp"', html)
		self.assertIn(SABA_URL, html)

	def test_print_without_stamp_keeps_signature_box(self):
		html = self.render(self.submitted_invoice(group=NO_STAMP_GROUP))

		self.assertNotIn('class="sign-stamp"', html)
		self.assertIn("Authorized Signature", html)

	def test_mobile_html_has_absolute_stamp_url(self):
		invoice = self.submitted_invoice(group=STAMP_GROUP)
		frappe.db.set_single_value(SETTINGS, "si_print_format", PRINT_FORMAT)

		get_document_html("Sales Invoice", invoice)

		self.assertEqual(frappe.response["status_code"], 200)
		self.assertIn(f'src="{get_url()}{SABA_URL}"', frappe.response["data"]["html"])

	def render(self, invoice):
		return frappe.get_print("Sales Invoice", invoice, print_format=PRINT_FORMAT)

	def submitted_invoice(self, group):
		"""Name of a submitted Saba invoice moved to `group`. The savepoint undoes the move."""
		name = frappe.db.get_value(
			"Sales Invoice", {"docstatus": 1, "naming_series": ("not like", "GW%")}, order_by="creation desc"
		)
		if not name:
			self.skipTest("The site has no submitted Saba Sales Invoice.")

		frappe.db.set_value("Sales Invoice", name, "customer_group", group, update_modified=False)
		return name
