# Copyright (c) 2026, Akwad Programming and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from sabaa.patches.enable_invoice_stamp_for_woqod_groups import WOQOD_GROUPS, execute

PATCH_MODULE = "sabaa.patches.enable_invoice_stamp_for_woqod_groups"
STAMP_FLAG = "custom_print_stamp_on_invoice"


class SavepointTestCase(FrappeTestCase):
	def setUp(self):
		frappe.db.savepoint("test_invoice_stamp")
		self.addCleanup(lambda: frappe.db.rollback(save_point="test_invoice_stamp"))


class TestInvoiceStampSchema(FrappeTestCase):
	def test_customer_group_has_stamp_flag(self):
		field = frappe.get_meta("Customer Group").get_field(STAMP_FLAG)
		self.assertEqual(field.fieldtype, "Check")

	def test_app_settings_has_stamp_images_in_own_section(self):
		meta = frappe.get_meta("App Settings")
		self.assertEqual(meta.get_field("custom_invoice_stamp_section").fieldtype, "Section Break")
		for fieldname in ("custom_saba_invoice_stamp", "custom_green_world_invoice_stamp"):
			self.assertEqual(meta.get_field(fieldname).fieldtype, "Attach Image")


class TestEnableWoqodGroups(SavepointTestCase):
	def test_patch_ticks_existing_woqod_groups(self):
		for name in WOQOD_GROUPS:
			make_customer_group(name)

		execute()

		for name in WOQOD_GROUPS:
			self.assertEqual(frappe.db.get_value("Customer Group", name, STAMP_FLAG), 1)

	def test_patch_skips_missing_group(self):
		make_customer_group("Woqod Group")

		with patch(f"{PATCH_MODULE}.WOQOD_GROUPS", ("Woqod Group", "_Test Missing Group")):
			execute()

		self.assertEqual(frappe.db.get_value("Customer Group", "Woqod Group", STAMP_FLAG), 1)


def make_customer_group(name, is_stamped=0):
	"""Get or create a leaf customer group and set its stamp flag."""
	if not frappe.db.exists("Customer Group", name):
		frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": name,
				"parent_customer_group": "All Customer Groups",
			}
		).insert()

	frappe.db.set_value("Customer Group", name, STAMP_FLAG, is_stamped)
	return name
