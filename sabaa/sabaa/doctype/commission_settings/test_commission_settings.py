# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCommissionSettings(FrappeTestCase):
	def test_settings_requires_erpnext_start_date(self):
		settings = frappe.get_single("Commission Settings")
		settings.erpnext_start_date = None
		with self.assertRaises(frappe.MandatoryError):
			settings.save()

	def test_patches_created_role_and_field(self):
		self.assertTrue(frappe.db.exists("Role", "Commission Manager"))
		self.assertTrue(frappe.get_meta("Sales Invoice").has_field("is_tender"))
