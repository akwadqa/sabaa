# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PurchaseAnalysisSettings(Document):
	def validate(self):
		self.validate_warehouse_groups()

	def validate_warehouse_groups(self):
		"""Nested groups would count the same stock twice in the warehouse split."""
		if not (self.main_store_warehouse and self.van_sales_warehouse):
			return

		main, van = (
			frappe.db.get_value("Warehouse", name, ["lft", "rgt"], as_dict=True)
			for name in (self.main_store_warehouse, self.van_sales_warehouse)
		)
		if main.lft <= van.lft < main.rgt or van.lft <= main.lft < van.rgt:
			frappe.throw(
				_("Main Store Warehouse {0} and Van Sales Warehouse {1} cannot be inside each other").format(
					frappe.bold(self.main_store_warehouse), frappe.bold(self.van_sales_warehouse)
				)
			)

	@property
	def promotional_markers(self) -> list[str]:
		lines = (self.promotional_name_markers or "").splitlines()
		return [line.strip().casefold() for line in lines if line.strip()]

	@property
	def promotional_uom_names(self) -> set[str]:
		return {row.uom for row in self.promotional_uoms}

	def is_promotional(self, item_name: str, stock_uom: str) -> bool:
		if stock_uom in self.promotional_uom_names:
			return True

		name = (item_name or "").casefold()
		return any(marker in name for marker in self.promotional_markers)
