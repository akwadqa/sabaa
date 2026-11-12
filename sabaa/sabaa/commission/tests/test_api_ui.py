# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from sabaa.sabaa.commission import api
from sabaa.sabaa.commission.default_plan import DEFAULT_PLAN_NAME
from sabaa.sabaa.commission.tests.factories import make_employee, make_plan, make_sales_person

COMPANY = "Saba Trading Group"


class TestSetupApi(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_api_ui"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))
		frappe.db.set_single_value("Commission Settings", {"erpnext_start_date": "2026-05-01", "company": COMPANY})

		self.plan = make_plan("Test UI Plan", "2026-01-01", "2026-12-31", "Draft").name
		self.group = make_sales_person("Test UI Team", is_group=1)
		self.employee = make_employee("Test UI Salesman", "Salesman") if frappe.db.exists("Designation", "Salesman") else None
		self.sales_person = make_sales_person("Test UI SP", self.employee, self.group)

	def make_rule(self, rule_name, **fields):
		values = {"doctype": "Commission Rule", "plan": self.plan, "rule_name": rule_name, "category": "Modern Trade"}
		values.update(fields)
		return frappe.get_doc(values).insert().name

	def test_setup_status_for_default_plan(self):
		if frappe.db.exists("Commission Plan", DEFAULT_PLAN_NAME):
			self.skipTest("default plan already exists on this site")
		plan = api.create_default_plan(COMPANY)

		rows = [row for row in api.get_setup_status(plan, "2026-06-01") if row["name"]]

		self.assertEqual(len(rows), 12)
		statuses = {row["rule_name"]: row["status"] for row in rows}
		self.assertEqual(statuses["Logistics – Team"], "Waiting for business input")

	def test_exclude_creates_assignment_from_month_start(self):
		rule = self.make_rule("Team Rule", team_group=self.group, is_waiting_for_business=1)

		api.save_people(rule, "2026-06-15", [{"employee": self.employee, "exclude": 1}])

		row = frappe.get_all("Commission Assignment", filters={"rule": rule}, fields=["assignment_type", "from_date"])[0]
		self.assertEqual((row.assignment_type, row.from_date), ("Exclude", getdate("2026-06-01")))
		people = api.get_people(rule, "2026-06-01")
		self.assertTrue(next(p for p in people if p["employee"] == self.employee)["excluded"])

	def test_pool_shares_must_total_100(self):
		other = make_employee("Test UI Other")
		rule = self.make_rule(
			"Pool Rule", recipient_source="Pool", is_waiting_for_business=1,
			shares=[{"share_name": "Salespersons", "percent": 100, "split": "By Assignment %"}],
		)

		with self.assertRaisesRegex(frappe.ValidationError, "Shares total 95%. They must total 100%."):
			api.save_people(rule, "2026-06-01", [{"employee": self.employee, "percent": 60}, {"employee": other, "percent": 35}])

		api.save_people(rule, "2026-06-01", [{"employee": self.employee, "percent": 60}, {"employee": other, "percent": 40}])
		percents = {p["employee"]: p["percent"] for p in api.get_people(rule, "2026-06-01")}
		self.assertEqual(percents, {self.employee: 60, other: 40})

	def test_missing_figures_round_trip(self):
		rule = self.make_rule("Avg Rule", team_group=self.group, period_mode="Rolling 3-Month Average", is_waiting_for_business=1)

		grid = api.get_missing_figure_grid(self.plan)
		self.assertEqual(grid["months"], ["2026-03-01", "2026-04-01"])
		api.save_missing_figures(self.plan, [{"rule": rule, "sales_person": self.sales_person, "month": "2026-04-01", "amount": 90000}])

		rows = api.get_missing_figure_grid(self.plan)["rules"][0]["rows"]
		row = next(r for r in rows if r["sales_person"] == self.sales_person)
		self.assertEqual(row["values"], {"2026-03-01": None, "2026-04-01": 90000})

	def test_add_share_member_and_copy_plan_keeps_people(self):
		rule = self.make_rule(
			"Tender Pool", category="Tenders", recipient_source="Pool", is_waiting_for_business=1,
			shares=[{"share_name": "Management", "percent": 100, "split": "Equal"}],
		)
		api.save_people(rule, "2026-06-01", [{"employee": self.employee, "share_name": "Management"}])
		self.assertEqual(api.get_people(rule, "2026-06-01")[0]["share_name"], "Management")

		new_plan = api.copy_plan(self.plan, "Test UI Plan Copy", "2026-07-01", "2026-12-31")

		new_rule = frappe.db.get_value("Commission Rule", {"plan": new_plan, "rule_name": "Tender Pool"})
		rows = frappe.get_all("Commission Assignment", filters={"rule": new_rule}, fields=["employee", "share_name", "from_date"])
		self.assertEqual([(r.employee, r.share_name, r.from_date) for r in rows], [(self.employee, "Management", getdate("2026-07-01"))])
