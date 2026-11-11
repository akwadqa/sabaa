# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from sabaa.sabaa.commission.default_plan import DEFAULT_PLAN_NAME, create_default_plan

COMPANY = "Saba Trading Group"


class TestDefaultPlan(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_default_plan"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))
		if frappe.db.exists("Commission Plan", DEFAULT_PLAN_NAME):
			for rule in frappe.get_all("Commission Rule", filters={"plan": DEFAULT_PLAN_NAME}, pluck="name"):
				frappe.delete_doc("Commission Rule", rule, force=1)
			frappe.delete_doc("Commission Plan", DEFAULT_PLAN_NAME, force=1)

	def test_creates_twelve_rules_once(self):
		plan = create_default_plan(COMPANY)

		self.assertEqual(create_default_plan(COMPANY), plan)
		self.assertEqual(frappe.db.count("Commission Rule", {"plan": plan}), 12)

	def test_supervisor_tiers_match_the_map(self):
		plan = create_default_plan(COMPANY)
		rule = frappe.get_doc("Commission Rule", {"plan": plan, "rule_name": "Traditional Trade – Supervisor"})

		rows = [(t.threshold, t.fixed_amount, t.excess_percent) for t in rule.tiers]
		self.assertEqual(rows, [(672000, 1344, 0), (840000, 2646, 0), (1050000, 4966.5, 0), (1260000, 7938, 1)])
		salesperson = frappe.db.get_value("Commission Rule", {"plan": plan, "rule_name": "Traditional Trade – Salesperson"})
		self.assertEqual(rule.paired_rule, salesperson)

	def test_open_questions_are_waiting(self):
		plan = create_default_plan(COMPANY)

		waiting = frappe.get_all("Commission Rule", filters={"plan": plan, "is_waiting_for_business": 1}, pluck="rule_name")
		self.assertEqual(
			sorted(waiting),
			sorted(["Logistics – Team", "Tenders", "Modern Trade – Salesperson Pool", "Traditional Trade – Cashier Assistant"]),
		)
		excluded = frappe.get_doc("Commission Plan", plan).excluded_customer_groups
		self.assertEqual([row.customer_group for row in excluded], ["Direct Sales"])
