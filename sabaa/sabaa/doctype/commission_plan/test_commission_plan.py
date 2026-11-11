# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from sabaa.sabaa.doctype.commission_plan.commission_plan import CommissionPlan

COMPANY = "Saba Trading Group"


def make_plan(plan_name: str, valid_from: str, valid_to: str | None, status: str = "Active"):
	return frappe.get_doc(
		{
			"doctype": "Commission Plan",
			"plan_name": plan_name,
			"company": COMPANY,
			"valid_from": valid_from,
			"valid_to": valid_to,
			"status": status,
		}
	).insert()


class TestCommissionPlan(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_commission_plan"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))
		frappe.db.set_value("Commission Plan", {"company": COMPANY, "status": "Active"}, "status", "Closed")

	def test_active_plans_cannot_overlap(self):
		first = make_plan("Test Plan A", "2026-01-01", "2026-12-31")
		with self.assertRaises(frappe.ValidationError) as raised:
			make_plan("Test Plan B", "2026-06-01", "2027-06-30")
		self.assertIn(first.name, str(raised.exception))

	def test_draft_plan_may_overlap_active_plan(self):
		make_plan("Test Plan A", "2026-01-01", "2026-12-31")
		make_plan("Test Plan B", "2026-06-01", None, status="Draft")

	def test_adjacent_active_plans_are_allowed(self):
		make_plan("Test Plan A", "2026-01-01", "2026-12-31")
		make_plan("Test Plan B", "2027-01-01", None)

	def test_valid_to_before_valid_from_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			make_plan("Test Plan A", "2026-06-01", "2026-05-01")

	def test_get_active_plan(self):
		plan = make_plan("Test Plan A", "2026-01-01", "2026-12-31")
		self.assertEqual(CommissionPlan.get_active_plan(COMPANY, getdate("2026-05-15")), plan.name)
		self.assertIsNone(CommissionPlan.get_active_plan(COMPANY, getdate("2027-01-01")))
