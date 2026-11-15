# Copyright (c) 2026, Akwad Programming and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from sabaa.patches import set_purchase_analysis_settings

COMPANY = "Saba Trading Group"
SETTINGS = "Purchase Analysis Settings"


class TestPurchaseAnalysisSettings(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_purchase_analysis_settings"
		frappe.db.savepoint(self._savepoint)
		# Saving the settings caches them; the rollback does not clear that cache.
		self.addCleanup(frappe.clear_document_cache, SETTINGS, SETTINGS)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

	def test_promotional_items_match_by_marker_or_uom(self):
		settings = self.make_settings(
			promotional_name_markers="G.P\n C.P \n\n", promotional_uoms=[{"uom": "Box"}]
		)

		self.assertTrue(settings.is_promotional("Mudhish Tortilla Pizza -1x24x20gm-G.P", "Outer"))
		self.assertTrue(settings.is_promotional("Mudhish Milk Pouch 1X400 Gm -g.p", "Pcs"))
		self.assertTrue(settings.is_promotional("Baja Peanuts Salted-24x13gm C.P", "Pcs"))
		self.assertTrue(settings.is_promotional("KIFCO Rusks Plain 1x24x385gm", "Box"))
		self.assertFalse(settings.is_promotional("Mudhish Tortilla Pizza -1x4x24x20 Gm", "Pcs"))

	def test_nested_warehouse_groups_are_rejected(self):
		group = self.make_warehouse("PAI Test Group", is_group=1)
		child = self.make_warehouse("PAI Test Van", parent_warehouse=group)
		sibling = self.make_warehouse("PAI Test Store")

		with self.assertRaises(frappe.ValidationError):
			self.make_settings(
				main_store_warehouse=group, van_sales_warehouse=child
			).validate_warehouse_groups()
		self.make_settings(
			main_store_warehouse=sibling, van_sales_warehouse=child
		).validate_warehouse_groups()

	def test_setup_patch_fills_only_blank_values(self):
		van_group = self.make_warehouse("PAI Test Van Group", is_group=1)
		settings = frappe.get_single(SETTINGS)
		settings.update(
			{
				"main_store_warehouse": None,
				"van_sales_warehouse": van_group,
				"promotional_name_markers": "C.P",
			}
		)
		settings.set("promotional_uoms", [])
		settings.save()

		set_purchase_analysis_settings.execute()

		settings.reload()
		self.assertEqual(
			(settings.van_sales_warehouse, settings.promotional_name_markers), (van_group, "C.P")
		)
		existing_uoms = {uom for uom in ("Outer", "Set", "Box") if frappe.db.exists("UOM", uom)}
		self.assertEqual(settings.promotional_uom_names, existing_uoms)

		set_purchase_analysis_settings.execute()
		self.assertEqual(len(frappe.get_single(SETTINGS).promotional_uoms), len(existing_uoms))

	def make_settings(self, **values):
		return frappe.get_doc({"doctype": SETTINGS, **values})

	def make_warehouse(
		self, warehouse_name: str, is_group: int = 0, parent_warehouse: str | None = None
	) -> str:
		warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": warehouse_name,
				"company": COMPANY,
				"is_group": is_group,
				"parent_warehouse": parent_warehouse,
			}
		)
		return warehouse.insert().name
