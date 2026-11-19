# Copyright (c) 2026, Akwad Programming and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from sabaa.patches.enable_invoice_stamp_for_woqod_groups import WOQOD_GROUPS, execute
from sabaa.sabaa.invoice_stamp import InvoiceStampError, get_invoice_stamp_url

PATCH_MODULE = "sabaa.patches.enable_invoice_stamp_for_woqod_groups"
STAMP_FLAG = "custom_print_stamp_on_invoice"
SETTINGS = "App Settings"
STAMP_GROUP = "_Test Stamp Group"
NO_STAMP_GROUP = "_Test No Stamp Group"
SABA_URL = "/files/saba-stamp.png"
GW_URL = "/files/gw-stamp.png"


class SavepointTestCase(FrappeTestCase):
	def setUp(self):
		frappe.db.savepoint("test_invoice_stamp")
		# The rollback does not clear cached documents.
		self.addCleanup(frappe.clear_document_cache, SETTINGS, SETTINGS)
		self.addCleanup(frappe.clear_document_cache, "Customer Group", STAMP_GROUP)
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


class StampSetupTestCase(SavepointTestCase):
	def setUp(self):
		super().setUp()
		make_customer_group(STAMP_GROUP, is_stamped=1)
		make_customer_group(NO_STAMP_GROUP)
		frappe.db.set_single_value(
			SETTINGS, {"custom_saba_invoice_stamp": SABA_URL, "custom_green_world_invoice_stamp": GW_URL}
		)


class TestInvoiceStampRule(StampSetupTestCase):
	def test_submitted_invoice_of_flagged_group_gets_saba_stamp(self):
		self.assertEqual(get_invoice_stamp_url(make_invoice(series="SIV/.#")), SABA_URL)

	def test_gw_series_gets_green_world_stamp(self):
		self.assertEqual(get_invoice_stamp_url(make_invoice(series="GW/SIV/.#")), GW_URL)

	def test_empty_series_uses_saba_stamp(self):
		self.assertEqual(get_invoice_stamp_url(make_invoice(series=None)), SABA_URL)

	def test_submitted_return_gets_stamp(self):
		self.assertEqual(get_invoice_stamp_url(make_invoice(is_return=1)), SABA_URL)

	def test_draft_and_cancelled_get_no_stamp(self):
		self.assertIsNone(get_invoice_stamp_url(make_invoice(docstatus=0)))
		self.assertIsNone(get_invoice_stamp_url(make_invoice(docstatus=2)))

	def test_unflagged_group_gets_no_stamp(self):
		self.assertIsNone(get_invoice_stamp_url(make_invoice(group=NO_STAMP_GROUP)))

	def test_invoice_without_group_gives_no_stamp(self):
		self.assertIsNone(get_invoice_stamp_url(make_invoice(group=None)))

	def test_missing_brand_image_gives_no_stamp(self):
		frappe.db.set_single_value(SETTINGS, "custom_green_world_invoice_stamp", None)

		self.assertIsNone(get_invoice_stamp_url(make_invoice(series="GW/SIV/.#")))
		self.assertEqual(get_invoice_stamp_url(make_invoice(series="SIV/.#")), SABA_URL)

	def test_group_on_invoice_decides(self):
		customer = frappe.db.get_value("Customer", {"customer_group": ("!=", STAMP_GROUP)})

		self.assertEqual(get_invoice_stamp_url(make_invoice(customer=customer)), SABA_URL)

	def test_flag_change_shows_on_next_print(self):
		self.assertEqual(get_invoice_stamp_url(make_invoice()), SABA_URL)

		group = frappe.get_doc("Customer Group", STAMP_GROUP)
		group.custom_print_stamp_on_invoice = 0
		group.save()

		self.assertIsNone(get_invoice_stamp_url(make_invoice()))


class TestStampFileValidation(SavepointTestCase):
	def test_private_stamp_file_is_refused(self):
		settings = frappe.get_single(SETTINGS)
		settings.custom_saba_invoice_stamp = "/private/files/saba-stamp.png"

		with self.assertRaisesRegex(InvoiceStampError, "Saba Stamp"):
			settings.save()

	def test_public_stamp_file_is_accepted(self):
		settings = frappe.get_single(SETTINGS)
		settings.custom_saba_invoice_stamp = SABA_URL
		settings.custom_green_world_invoice_stamp = GW_URL
		settings.save()

		self.assertEqual(frappe.db.get_single_value(SETTINGS, "custom_saba_invoice_stamp"), SABA_URL)

	def test_jinja_method_is_registered(self):
		self.assertIn("sabaa.sabaa.invoice_stamp.get_invoice_stamp_url", frappe.get_hooks("jinja")["methods"])


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


def make_invoice(group=STAMP_GROUP, series="SIV/.#", docstatus=1, is_return=0, customer=None):
	"""Build an unsaved Sales Invoice with only the fields the stamp rule reads."""
	return frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": customer,
			"customer_group": group,
			"naming_series": series,
			"docstatus": docstatus,
			"is_return": is_return,
		}
	)
