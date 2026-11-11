# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import importlib

import frappe
from frappe.tests.utils import FrappeTestCase

from sabaa.sabaa.commission.tests.factories import (
	make_customer,
	make_customer_group,
	make_employee,
	make_plan,
	make_sales_invoice,
	make_sales_person,
	make_service_item,
)

report = importlib.import_module("sabaa.sabaa.report.sales_commission_&_incentive.sales_commission_&_incentive")
COMPANY = "Saba Trading Group"


class TestSalesCommissionReport(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_commission_report"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

		frappe.db.set_single_value("Commission Settings", {"erpnext_start_date": "2026-04-01", "company": COMPANY})
		frappe.db.set_value("Commission Plan", {"status": "Active"}, "status", "Draft")
		self.plan = make_plan("Test Report Plan", "2026-01-01", "2026-12-31").name
		self.employee = make_employee("Test Report Salesman")
		self.sales_person = make_sales_person("Test Report SP", self.employee)
		self.group = make_customer_group("Test Report Group")
		self.customer = make_customer("Test Report Customer", self.group)
		self.item = make_service_item("TEST-REPORT-ITEM")
		frappe.get_doc(
			{
				"doctype": "Commission Rule", "plan": self.plan, "rule_name": "Online", "category": "Smile24",
				"basis": "Net Invoiced Sales", "basis_sources": [{"customer_group": self.group, "measure": "Invoiced"}],
				"tiers": [{"threshold": t, "fixed_amount": f} for t, f in ((70000, 200), (84000, 367), (105000, 1050))],
			}
		).insert()

	def sell(self, posting_date, amount, sales_person="default"):
		person = self.sales_person if sales_person == "default" else sales_person
		make_sales_invoice(self.customer, person, posting_date, [(self.item, amount)])

	def run_report(self, **filters):
		values = {"company": COMPANY, "period_type": "Month", "month": "2026-05-01"}
		values.update(filters)
		return report.execute(values)

	def test_summary_has_employee_and_not_assigned_rows(self):
		self.sell("2026-05-05", 90000)
		self.sell("2026-05-06", 75000, sales_person=None)

		_columns, data, _message = self.run_report()

		self.assertEqual([(row["employee"], row["smile24"]) for row in data], [(self.employee, 367), (None, 200)])
		self.assertEqual(data[-1]["employee_name"], "Not assigned")

	def test_detail_shows_tier_label(self):
		self.sell("2026-05-05", 90000)

		_columns, data, _message = self.run_report(view="Detail")

		self.assertEqual((data[0]["tier_label"], data[0]["amount"]), ("2 of 3", 367))

	def test_no_plan_returns_message(self):
		columns, data, message = self.run_report(month="2030-01-01")

		self.assertEqual((columns, data, message), ([], [], "No active commission plan covers January 2030."))

	def test_quarter_sums_its_months(self):
		for posting_date in ("2026-04-05", "2026-05-05", "2026-06-05"):
			self.sell(posting_date, 90000)

		_columns, data, _message = self.run_report(period_type="Quarter", quarter="2026-Q2")

		self.assertEqual(data[0]["smile24"], 367 * 3)
