# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.stock.doctype.item.test_item import make_item
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today

from sabaa.sabaa.report.trading_sales_analytics.trading_sales_analytics import execute

PARENT_GROUP = "_Test TSA Customers"
RETAIL_GROUP = "_Test TSA Retail"
WHOLESALE_GROUP = "_Test TSA Wholesale"
SALES_TEAM = "_Test TSA Team"
ALI = "_Test TSA Ali"
SARA = "_Test TSA Sara"


class TestTradingSalesAnalytics(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase only rolls back at class teardown; each test posts real
		# invoices against the live company, so a savepoint isolates them.
		frappe.db.savepoint("test_trading_sales_analytics")
		self.addCleanup(lambda: frappe.db.rollback(save_point="test_trading_sales_analytics"))

		self.company = "Saba Trading Group"
		self.posting_date = today()

		self._make_tree_node("Customer Group", PARENT_GROUP, "parent_customer_group", "All Customer Groups", 1)
		self._make_tree_node("Customer Group", RETAIL_GROUP, "parent_customer_group", PARENT_GROUP, 0)
		self._make_tree_node("Customer Group", WHOLESALE_GROUP, "parent_customer_group", PARENT_GROUP, 0)
		self._make_tree_node("Sales Person", SALES_TEAM, "parent_sales_person", "Sales Team", 1)
		self._make_tree_node("Sales Person", ALI, "parent_sales_person", SALES_TEAM, 0)
		self._make_tree_node("Sales Person", SARA, "parent_sales_person", SALES_TEAM, 0)

		self.retail_customer = self._make_customer("_Test TSA Retail Customer", RETAIL_GROUP)
		self.wholesale_customer = self._make_customer("_Test TSA Wholesale Customer", WHOLESALE_GROUP)
		self.warehouse = frappe.get_all(
			"Warehouse", filters={"company": self.company, "is_group": 0}, limit=1
		)[0].name
		self.item = make_item("_Test TSA Item", {"item_group": "Canned Food", "is_stock_item": 0}).name

		self._make_invoice(self.retail_customer, qty=10, rate=100, sales_team={ALI: 60, SARA: 40})
		self._make_invoice(self.wholesale_customer, qty=5, rate=200, sales_team={SARA: 100})

	def _make_tree_node(self, doctype, name, parent_field, parent, is_group):
		name_field = "sales_person_name" if doctype == "Sales Person" else "customer_group_name"
		frappe.get_doc(
			{"doctype": doctype, name_field: name, parent_field: parent, "is_group": is_group}
		).insert()

	def _make_customer(self, name, customer_group):
		return frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_type": "Company",
				"customer_group": customer_group,
			}
		).insert().name

	def _make_invoice(self, customer, qty, rate, sales_team):
		company = frappe.get_cached_doc("Company", self.company)
		invoice = create_sales_invoice(
			company=self.company,
			customer=customer,
			item_code=self.item,
			qty=qty,
			rate=rate,
			warehouse=self.warehouse,
			currency=company.default_currency,
			debit_to=company.default_receivable_account,
			income_account=company.default_income_account,
			expense_account=company.default_expense_account,
			cost_center=company.cost_center,
			do_not_save=1,
		)
		# The site default customer_group ("All Customer Groups") is pre-filled on
		# server-created docs; the desk form replaces it with the customer's group.
		invoice.customer_group = frappe.db.get_value("Customer", customer, "customer_group")
		for sales_person, percentage in sales_team.items():
			invoice.append("sales_team", {"sales_person": sales_person, "allocated_percentage": percentage})
		invoice.insert()
		invoice.submit()

	def _run(self, **filters):
		_, data, *_ = execute(
			frappe._dict(
				{
					"tree_type": "Customer",
					"doc_type": "Sales Invoice",
					"value_quantity": "Value",
					"from_date": self.posting_date,
					"to_date": self.posting_date,
					"company": self.company,
					"range": "Monthly",
					**filters,
				}
			)
		)
		return {row["entity"]: row["total"] for row in data}

	def test_sales_person_value_is_split_by_allocated_percentage(self):
		totals = self._run(tree_type="Sales Person", sales_person=[SALES_TEAM])

		self.assertEqual(flt(totals[ALI]), 600)
		self.assertEqual(flt(totals[SARA]), 1400)
		self.assertEqual(flt(totals[SALES_TEAM]), 2000)

	def test_sales_person_quantity_is_split_by_allocated_percentage(self):
		totals = self._run(tree_type="Sales Person", value_quantity="Quantity", sales_person=[SALES_TEAM])

		self.assertEqual(flt(totals[ALI]), 6)
		self.assertEqual(flt(totals[SARA]), 9)

	def test_sales_person_filter_hides_unselected_sales_persons(self):
		totals = self._run(tree_type="Sales Person", sales_person=[ALI])

		self.assertEqual(flt(totals[ALI]), 600)
		self.assertNotIn(SARA, totals)
		self.assertTrue(all(flt(total) for total in totals.values()))

	def test_sales_person_with_customer_group_filter(self):
		totals = self._run(tree_type="Sales Person", sales_person=[SALES_TEAM], customer_group=[RETAIL_GROUP])

		self.assertEqual(flt(totals[ALI]), 600)
		self.assertEqual(flt(totals[SARA]), 400)

	def test_customer_group_with_sales_person_filter_counts_invoice_once(self):
		totals = self._run(tree_type="Customer Group", sales_person=[ALI, SARA], customer_group=[PARENT_GROUP])

		self.assertEqual(flt(totals[RETAIL_GROUP]), 1000)
		self.assertEqual(flt(totals[WHOLESALE_GROUP]), 1000)
		self.assertEqual(flt(totals[PARENT_GROUP]), 2000)

	def test_customer_with_both_filters(self):
		totals = self._run(sales_person=[SARA], customer_group=[RETAIL_GROUP])

		self.assertEqual(totals, {self.retail_customer: 1000})

	def test_item_with_sales_person_filter(self):
		totals = self._run(tree_type="Item", sales_person=[ALI])

		self.assertEqual(totals, {self.item: 1000})

	def test_customer_without_new_filters_is_unchanged(self):
		totals = self._run()

		self.assertEqual(flt(totals[self.retail_customer]), 1000)
		self.assertEqual(flt(totals[self.wholesale_customer]), 1000)
