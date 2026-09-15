# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.stock.doctype.item.test_item import make_item
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today

from sabaa.sabaa.report.saba_excise_tax_report.saba_excise_tax_report import execute


class TestSabaExciseTaxReport(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase only rolls back at class teardown, not per test; each
		# test posts real GL/stock transactions against the live company, so an
		# explicit savepoint keeps the tests isolated from one another.
		self._savepoint = "test_saba_excise_tax_report"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

		self.company = "Saba Trading Group"
		self.account = frappe.get_cached_value(
			"Company", self.company, "custom_excise_tax_recoverable_account"
		)
		self.receivable_account = frappe.get_cached_value(
			"Company", self.company, "default_receivable_account"
		)
		self.income_account = frappe.get_cached_value("Company", self.company, "default_income_account")
		self.expense_account = frappe.get_cached_value("Company", self.company, "default_expense_account")
		self.cash_account = frappe.get_cached_value("Company", self.company, "default_cash_account")
		self.cost_center = frappe.get_cached_value("Company", self.company, "cost_center")
		self.warehouse = frappe.get_all(
			"Warehouse", filters={"company": self.company, "is_group": 0}, limit=1
		)[0].name
		self.customer = frappe.get_all("Customer", limit=1)[0].name
		self.posting_date = today()

		self.item = make_item(
			properties={
				"item_group": "Canned Food",
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"custom_is_excisable": 1,
				"custom_excise_rate": 5,
			}
		)

		self._receive_stock(qty=20, rate=50)

	def _receive_stock(self, qty, rate):
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Receipt"
		se.purpose = "Material Receipt"
		se.company = self.company
		se.posting_date = self.posting_date
		se.set_posting_time = 1
		se.append(
			"items",
			{
				"item_code": self.item.name,
				"t_warehouse": self.warehouse,
				"qty": qty,
				"basic_rate": rate,
				"cost_center": self.cost_center,
			},
		)
		se.insert()
		se.submit()

	def _make_damage_entry(self, qty):
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Damage"
		se.purpose = "Material Issue"
		se.company = self.company
		se.posting_date = self.posting_date
		se.set_posting_time = 1
		se.append(
			"items",
			{
				"item_code": self.item.name,
				"s_warehouse": self.warehouse,
				"qty": qty,
				"cost_center": self.cost_center,
				"expense_account": self.expense_account,
			},
		)
		se.insert()
		se.submit()
		return se

	def _make_customs_payment(self, amount):
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": self.posting_date,
				"accounts": [
					{"account": self.account, "debit_in_account_currency": amount},
					{"account": self.cash_account, "credit_in_account_currency": amount},
				],
			}
		)
		je.insert()
		je.submit()
		return je

	def test_report_totals_and_remaining_balance(self):
		si = create_sales_invoice(
			company=self.company,
			customer=self.customer,
			item_code=self.item.name,
			qty=10,
			rate=100,
			warehouse=self.warehouse,
			debit_to=self.receivable_account,
			income_account=self.income_account,
			expense_account=self.expense_account,
			cost_center=self.cost_center,
		)

		# Excise hook (sabaa.override.excise) must add 10 qty x 5 rate = 50
		self.assertEqual(flt(si.custom_total_excise), 50)

		self._make_customs_payment(200)
		self._make_damage_entry(qty=4)

		filters = frappe._dict(
			{"company": self.company, "from_date": self.posting_date, "to_date": self.posting_date}
		)
		_, data, _, _, report_summary = execute(filters)

		self.assertEqual(len(data), 1)
		row = data[0]
		self.assertEqual(flt(row["paid_to_customs"]), 200)
		self.assertEqual(flt(row["recovered_from_si"]), 50)
		self.assertEqual(flt(row["expired_damaged_excise"]), 20)
		self.assertEqual(flt(row["remaining_balance"]), 130)

		summary_by_label = {entry["label"]: entry["value"] for entry in report_summary}
		self.assertEqual(flt(summary_by_label["Remaining Balance"]), 130)

	def test_report_details_rows(self):
		create_sales_invoice(
			company=self.company,
			customer=self.customer,
			item_code=self.item.name,
			qty=2,
			rate=100,
			warehouse=self.warehouse,
			debit_to=self.receivable_account,
			income_account=self.income_account,
			expense_account=self.expense_account,
			cost_center=self.cost_center,
		)
		self._make_customs_payment(100)
		self._make_damage_entry(qty=1)

		filters = frappe._dict(
			{
				"company": self.company,
				"from_date": self.posting_date,
				"to_date": self.posting_date,
				"show_details": 1,
			}
		)
		_, data, *_ = execute(filters)

		self.assertEqual(len(data), 3)
		categories = {row["category"] for row in data}
		self.assertIn("Paid to Customs", categories)
		self.assertIn("Recovered from Sales Invoices", categories)
		self.assertTrue(any("Expired/Damaged Excise" in c for c in categories))

	def test_non_excisable_item_is_ignored(self):
		plain_item = make_item(properties={"item_group": "Canned Food", "is_stock_item": 1})
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Receipt"
		se.purpose = "Material Receipt"
		se.company = self.company
		se.posting_date = self.posting_date
		se.set_posting_time = 1
		se.append(
			"items",
			{
				"item_code": plain_item.name,
				"t_warehouse": self.warehouse,
				"qty": 10,
				"basic_rate": 20,
				"cost_center": self.cost_center,
			},
		)
		se.insert()
		se.submit()

		damage = frappe.new_doc("Stock Entry")
		damage.stock_entry_type = "Damage"
		damage.purpose = "Material Issue"
		damage.company = self.company
		damage.posting_date = self.posting_date
		damage.set_posting_time = 1
		damage.append(
			"items",
			{
				"item_code": plain_item.name,
				"s_warehouse": self.warehouse,
				"qty": 5,
				"cost_center": self.cost_center,
				"expense_account": self.expense_account,
			},
		)
		damage.insert()
		damage.submit()

		filters = frappe._dict(
			{"company": self.company, "from_date": self.posting_date, "to_date": self.posting_date}
		)
		_, data, *_ = execute(filters)
		self.assertEqual(flt(data[0]["expired_damaged_excise"]), 0)
