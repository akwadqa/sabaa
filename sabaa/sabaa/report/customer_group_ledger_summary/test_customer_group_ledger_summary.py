# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.customer_ledger_summary.customer_ledger_summary import (
	execute as native_execute,
)
from erpnext.stock.doctype.item.test_item import make_item
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today

from sabaa.sabaa.report.customer_group_ledger_summary.customer_group_ledger_summary import execute

ROOT = "All Customer Groups"
TOP = "_Test CGLS Top"
MID = "_Test CGLS Mid"
LEAF_A = "_Test CGLS Leaf A"
LEAF_B = "_Test CGLS Leaf B"
SOLO = "_Test CGLS Solo"
EMPTY = "_Test CGLS Empty"
AMOUNT_FIELDS = (
	"opening_balance",
	"invoiced_amount",
	"paid_amount",
	"return_amount",
	"adjustment_amount",
	"closing_balance",
)


class TestCustomerGroupLedgerSummary(FrappeTestCase):
	def setUp(self):
		# Each test posts real GL entries against the live company; a savepoint isolates them.
		frappe.db.savepoint("test_customer_group_ledger_summary")
		self.addCleanup(lambda: frappe.db.rollback(save_point="test_customer_group_ledger_summary"))

		self.company = "Saba Trading Group"
		self.company_doc = frappe.get_cached_doc("Company", self.company)
		self.warehouse = frappe.get_all(
			"Warehouse", filters={"company": self.company, "is_group": 0}, limit=1
		)[0].name
		self.item = make_item("_Test CGLS Item", {"item_group": "Canned Food", "is_stock_item": 0}).name

		self._make_group(TOP, ROOT, 1)
		self._make_group(MID, TOP, 1)
		self._make_group(LEAF_A, MID, 0)
		self._make_group(LEAF_B, MID, 0)
		self._make_group(SOLO, ROOT, 0)
		self._make_group(EMPTY, MID, 0)

		customer_a = self._make_customer("_Test CGLS A1", LEAF_A)
		invoice_a = self._make_invoice(customer_a, qty=10, rate=100)
		self._make_payment(invoice_a, 400)
		self._make_invoice(customer_a, qty=-1, rate=100, is_return=1, return_against=invoice_a)

		self._make_invoice(self._make_customer("_Test CGLS B1", LEAF_B), qty=5, rate=100)
		# ERPNext blocks group nodes on new customers, but the live site has legacy customers
		# directly on group nodes (for example "Saba Customers"), so set it directly.
		customer_m = self._make_customer("_Test CGLS M1", LEAF_B)
		self._make_invoice(customer_m, qty=5, rate=100)
		frappe.db.set_value("Customer", customer_m, "customer_group", MID)
		self._make_invoice(self._make_customer("_Test CGLS S1", SOLO), qty=5, rate=100)

	def _make_group(self, name, parent, is_group):
		frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": name,
				"parent_customer_group": parent,
				"is_group": is_group,
			}
		).insert()

	def _make_customer(self, name, customer_group):
		return (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": name,
					"customer_type": "Company",
					"customer_group": customer_group,
				}
			)
			.insert()
			.name
		)

	def _make_invoice(self, customer, qty, rate, **kwargs):
		invoice = create_sales_invoice(
			company=self.company,
			customer=customer,
			item_code=self.item,
			qty=qty,
			rate=rate,
			warehouse=self.warehouse,
			currency=self.company_doc.default_currency,
			debit_to=self.company_doc.default_receivable_account,
			income_account=self.company_doc.default_income_account,
			expense_account=self.company_doc.default_expense_account,
			cost_center=self.company_doc.cost_center,
			do_not_save=1,
			**kwargs,
		)
		invoice.customer_group = frappe.db.get_value("Customer", customer, "customer_group")
		invoice.taxes = []
		invoice.insert()
		invoice.submit()
		return invoice.name

	def _make_payment(self, invoice, amount):
		payment = get_payment_entry(
			"Sales Invoice", invoice, party_amount=amount, bank_account=self.company_doc.default_cash_account
		)
		payment.reference_no = "_Test CGLS"
		payment.reference_date = today()
		payment.insert()
		payment.submit()

	def _filters(self, **filters):
		return frappe._dict(
			{
				"company": self.company,
				"from_date": today(),
				"to_date": today(),
				"customer_group": TOP,
				**filters,
			}
		)

	def _execute(self, **filters):
		_columns, data, _message, _chart, summary = execute(self._filters(**filters))
		return data, {card["label"]: card["value"] for card in summary}

	def _run(self, **filters):
		data, _summary = self._execute(**filters)
		return {row["customer_group"]: row for row in data}

	def test_tree_rows_roll_up_children(self):
		rows = self._run()

		self.assertEqual(flt(rows[TOP].invoiced_amount), 2000)
		self.assertEqual(flt(rows[MID].invoiced_amount), 2000)
		self.assertEqual(flt(rows[MID].paid_amount), 400)
		self.assertEqual(flt(rows[MID].return_amount), 100)
		self.assertEqual(flt(rows[MID].closing_balance), 1500)
		self.assertEqual(rows[MID].customer_count, 3)
		self.assertEqual(flt(rows[LEAF_A].invoiced_amount), 1000)
		self.assertEqual(flt(rows[LEAF_B].invoiced_amount), 500)

	def test_tree_rows_have_indent_and_parent(self):
		rows = self._run()

		self.assertEqual((rows[TOP].indent, rows[TOP].parent_customer_group), (0, None))
		self.assertEqual((rows[MID].indent, rows[MID].parent_customer_group), (1, TOP))
		self.assertEqual((rows[LEAF_A].indent, rows[LEAF_A].parent_customer_group), (2, MID))

	def test_parent_listed_before_children(self):
		data, _summary = self._execute()
		order = [row.customer_group for row in data]

		self.assertEqual(order, [TOP, MID, LEAF_A, LEAF_B])

	def test_groups_without_activity_are_hidden(self):
		self.assertNotIn(EMPTY, self._run())

	def test_customer_on_group_node_counts_in_its_own_row(self):
		rows = self._run()

		# M1 sits directly on MID, so MID is more than the sum of its children.
		self.assertEqual(rows[MID].customer_count, 3)
		self.assertEqual(rows[LEAF_A].customer_count + rows[LEAF_B].customer_count, 2)

	def test_leaf_under_root_is_top_level_row(self):
		rows = self._run(customer_group=SOLO)

		self.assertEqual(list(rows), [SOLO])
		self.assertEqual(rows[SOLO].indent, 0)

	def test_cards_match_native_totals(self):
		filters = self._filters(customer_group=ROOT)
		_, native_rows = native_execute(frappe._dict(filters))
		_data, cards = self._execute(customer_group=ROOT)

		expected = {
			"Total Sales": "invoiced_amount",
			"Total Paid": "paid_amount",
			"Total Return": "return_amount",
			"Closing Balance": "closing_balance",
		}
		for label, field in expected.items():
			self.assertAlmostEqual(flt(cards[label]), sum(flt(row[field]) for row in native_rows), places=2)

	def test_top_level_rows_sum_to_native_totals(self):
		filters = self._filters(customer_group=ROOT)
		_, native_rows = native_execute(frappe._dict(filters))
		data, _cards = self._execute(customer_group=ROOT)
		top_rows = [row for row in data if row.indent == 0]

		for field in ("invoiced_amount", "paid_amount", "return_amount", "closing_balance"):
			self.assertAlmostEqual(
				sum(flt(row[field]) for row in top_rows),
				sum(flt(row[field]) for row in native_rows),
				places=2,
			)

	def test_no_data_returns_empty(self):
		data, cards = self._execute(customer_group=LEAF_B, from_date="2000-01-01", to_date="2000-01-02")

		self.assertEqual(data, [])
		self.assertEqual(flt(cards["Total Sales"]), 0)

	def test_customer_without_group_is_listed_last(self):
		customer = self._make_customer("_Test CGLS No Group", SOLO)
		self._make_invoice(customer, qty=2, rate=100)
		frappe.db.set_value("Customer", customer, "customer_group", None)

		data, _cards = self._execute(customer_group=None)

		self.assertIsNone(data[-1].customer_group)
		self.assertEqual(data[-1].indent, 0)
		self.assertGreaterEqual(flt(data[-1].invoiced_amount), 200)

	def test_adjustments_reconcile_closing(self):
		# The native report moves write-offs out of Paid into dynamic adj_<account> columns.
		native_columns = [{"fieldname": "adj_write_off", "is_adjustment": 1}]
		native_rows = [
			frappe._dict(
				party="_Test CGLS A1",
				customer_group=LEAF_A,
				currency="QAR",
				opening_balance=0,
				invoiced_amount=1000,
				paid_amount=350,
				return_amount=100,
				adj_write_off=50,
				closing_balance=500,
			)
		]
		with patch(
			f"{execute.__module__}.customer_ledger_summary", return_value=(native_columns, native_rows)
		):
			rows = self._run()

		row = rows[LEAF_A]
		self.assertEqual(flt(row.adjustment_amount), 50)
		self.assertEqual(
			row.opening_balance
			+ row.invoiced_amount
			- row.paid_amount
			- row.return_amount
			- row.adjustment_amount,
			row.closing_balance,
		)
