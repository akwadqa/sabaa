# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.doctype.item.test_item import make_item
from frappe.desk.query_report import run
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from sabaa.sabaa.report.stock_ledger_quantity.stock_ledger_quantity import execute, is_value_field

REPORT_NAME = "Stock Ledger Quantity"


class TestStockLedgerQuantity(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase only rolls back at class teardown; the tests post real stock entries.
		self._savepoint = "test_stock_ledger_quantity"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

		self.company = "Saba Trading Group"
		self.warehouse = frappe.get_all(
			"Warehouse", filters={"company": self.company, "is_group": 0}, limit=1
		)[0].name
		self.item = make_item(
			properties={
				"item_group": "Canned Food",
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"uoms": [{"uom": "Nos", "conversion_factor": 1}, {"uom": "Box", "conversion_factor": 12}],
			}
		)

		self._make_stock_entry("Material Receipt", qty=24, rate=50, posting_date=add_days(today(), -1))
		self._make_stock_entry("Material Issue", qty=10, rate=50, posting_date=today())

	def _make_stock_entry(self, purpose, qty, rate, posting_date):
		warehouse_field = "t_warehouse" if purpose == "Material Receipt" else "s_warehouse"
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = purpose
		stock_entry.purpose = purpose
		stock_entry.company = self.company
		stock_entry.posting_date = posting_date
		stock_entry.set_posting_time = 1
		stock_entry.append(
			"items",
			{
				"item_code": self.item.name,
				warehouse_field: self.warehouse,
				"qty": qty,
				"basic_rate": rate,
				"cost_center": frappe.get_cached_value("Company", self.company, "cost_center"),
			},
		)
		stock_entry.insert()
		stock_entry.submit()

	def _get_filters(self, **extra):
		return frappe._dict(
			company=self.company,
			from_date=today(),
			to_date=today(),
			item_code=[self.item.name],
			warehouse=[self.warehouse],
			**extra,
		)

	def assert_no_value_fields(self, columns, data):
		self.assertFalse([column["fieldname"] for column in columns if is_value_field(column["fieldname"])])
		self.assertFalse([key for row in data for key in row if is_value_field(key)])

	def test_shows_quantities_with_opening_balance(self):
		columns, data = execute(self._get_filters())

		fieldnames = {column["fieldname"] for column in columns}
		self.assertTrue({"in_qty", "out_qty", "qty_after_transaction"} <= fieldnames)
		self.assert_no_value_fields(columns, data)

		opening_row, issue_row = data
		self.assertEqual(opening_row["qty_after_transaction"], 24)
		self.assertEqual(issue_row["out_qty"], -10)
		self.assertEqual(issue_row["qty_after_transaction"], 14)

	def test_include_uom_adds_only_quantity_columns(self):
		columns, data = execute(self._get_filters(include_uom="Box"))

		self.assert_no_value_fields(columns, data)
		self.assertIn("qty_after_transaction_box", {column["fieldname"] for column in columns})
		self.assertAlmostEqual(data[-1]["qty_after_transaction_box"], 14 / 12, places=3)

	def test_sales_user_can_run_report(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "stock_ledger_qty_sales@example.com",
				"first_name": "Sales",
				"roles": [{"role": "Sales User"}],
			}
		).insert(ignore_permissions=True)
		frappe.set_user(user.name)
		self.addCleanup(frappe.set_user, "Administrator")

		result = run(REPORT_NAME, filters=self._get_filters())

		self.assertEqual(result["result"][-1]["qty_after_transaction"], 14)
		self.assert_no_value_fields(result["columns"], result["result"])
