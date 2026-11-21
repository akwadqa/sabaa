# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.doctype.item.test_item import make_item
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from sabaa.sabaa.report.transaction_summary_report___daybook.transaction_summary_report___daybook import (
	execute,
	get_line_rows,
	get_transaction_codes,
)


def line(**kwargs):
	return frappe._dict({"qty": 5, "rate": 10, "cf": 1, "is_return": 0, **kwargs})


def codes_of(rows):
	return [row["code"] for row in rows]


class TestTransactionCodes(FrappeTestCase):
	def test_trade_vouchers(self):
		self.assertEqual(codes_of(get_line_rows(line(voucher_type="Sales Invoice", s_wh="W"))), ["SIV"])
		self.assertEqual(codes_of(get_line_rows(line(voucher_type="Delivery Note", s_wh="W"))), ["DN"])
		self.assertEqual(codes_of(get_line_rows(line(voucher_type="Purchase Receipt", s_wh="W"))), ["PIV"])
		self.assertEqual(codes_of(get_line_rows(line(voucher_type="Purchase Invoice", s_wh="W"))), ["PIV"])

	def test_returns_use_absolute_qty(self):
		rows = get_line_rows(line(voucher_type="Sales Invoice", is_return=1, qty=-3, s_wh="W"))
		self.assertEqual(codes_of(rows), ["CRN"])
		self.assertEqual(rows[0]["qty"], 3)
		self.assertEqual(codes_of(get_line_rows(line(voucher_type="Purchase Invoice", is_return=1, s_wh="W"))), ["DRN"])

	def test_stock_entry_transfer_gives_issue_and_receipt(self):
		rows = get_line_rows(line(voucher_type="Stock Entry", se_purpose="Material Transfer", s_wh="A", t_wh="B", cf=12))
		self.assertEqual([(r["code"], r["warehouse"], r["leg"]) for r in rows], [("STG-N", "A", 0), ("STG-P", "B", 1)])
		# basic_rate is per stock UOM; the report shows it per line UOM
		self.assertEqual(rows[0]["rate"], 120)

	def test_stock_entry_damage_expiry_repack(self):
		self.assertEqual(codes_of(get_line_rows(line(voucher_type="Stock Entry", se_type="Damage", s_wh="A"))), ["DAM"])
		self.assertEqual(codes_of(get_line_rows(line(voucher_type="Stock Entry", se_type="Expiry", s_wh="A"))), ["EXP"])
		rows = get_line_rows(line(voucher_type="Stock Entry", se_purpose="Repack", t_wh="B"))
		self.assertEqual([(r["code"], r["warehouse"], r["leg"]) for r in rows], [("GCN", "B", 1)])

	def test_stock_reconciliation(self):
		rows = get_line_rows(line(voucher_type="Stock Reconciliation", sr_purpose="Opening Stock", s_wh="A"))
		self.assertEqual(codes_of(rows), ["STK"])
		rows = get_line_rows(line(voucher_type="Stock Reconciliation", sr_purpose="Stock Reconciliation", qty=4, current_qty=6.5, s_wh="A"))
		self.assertEqual((rows[0]["code"], rows[0]["qty"]), ("SJ-NP", -2.5))

	def test_transaction_type_filter_formats(self):
		self.assertEqual(get_transaction_codes(frappe._dict(transaction_type=["SIV"])), ["SIV"])
		self.assertEqual(get_transaction_codes(frappe._dict(transaction_type='["SIV", "DN"]')), ["SIV", "DN"])
		self.assertEqual(get_transaction_codes(frappe._dict(transaction_type="SIV, DN")), ["SIV", "DN"])
		self.assertEqual(get_transaction_codes(frappe._dict()), [])


class TestTransactionSummaryReportDaybook(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase only rolls back at class teardown; the test posts real stock entries.
		self._savepoint = "test_transaction_summary_daybook"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

		self.company = "Saba Trading Group"
		warehouses = frappe.get_all("Warehouse", filters={"company": self.company, "is_group": 0}, limit=2, pluck="name")
		self.source, self.target = warehouses[0], warehouses[1]
		self.item = make_item(properties={"item_group": "Canned Food", "is_stock_item": 1, "stock_uom": "Nos"})

		self._make_stock_entry("Material Receipt", t_warehouse=self.source, qty=10)
		self.transfer = self._make_stock_entry("Material Transfer", s_warehouse=self.source, t_warehouse=self.target, qty=4)

	def _make_stock_entry(self, purpose, qty, **warehouses):
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = purpose
		stock_entry.purpose = purpose
		stock_entry.company = self.company
		stock_entry.posting_date = today()
		stock_entry.set_posting_time = 1
		stock_entry.append(
			"items",
			{
				"item_code": self.item.name,
				"qty": qty,
				"basic_rate": 25,
				"cost_center": frappe.get_cached_value("Company", self.company, "cost_center"),
				**warehouses,
			},
		)
		stock_entry.insert()
		stock_entry.submit()
		return stock_entry.name

	def _run(self, **extra):
		filters = {"company": self.company, "from_date": today(), "to_date": today(), "item_code": self.item.name}
		filters.update(extra)
		return execute(filters)

	def test_transfer_rows(self):
		columns, data = self._run()
		self.assertEqual(len(columns), 14)
		transfer_rows = [d for d in data if d["voucher_no"] == self.transfer]
		self.assertEqual([d["transaction_type"] for d in transfer_rows], ["STG-N", "STG-P"])
		self.assertEqual([d["warehouse"] for d in transfer_rows], [self.source, self.target])
		self.assertTrue(all(d["transfer_no"] == self.transfer and d["amount"] == 100 for d in transfer_rows))
		receipt = [d for d in data if d["voucher_no"] != self.transfer]
		self.assertEqual([(d["transaction_type"], d["transfer_no"]) for d in receipt], [("STG-P", None)])

	def test_filters(self):
		_, data = self._run(transaction_type=["STG-N"])
		self.assertEqual([d["transaction_type"] for d in data], ["STG-N"])
		_, data = self._run(warehouse=self.target)
		self.assertEqual([(d["transaction_type"], d["warehouse"]) for d in data], [("STG-P", self.target)])
