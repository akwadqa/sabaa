# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from sabaa.sabaa.commission.tests.factories import make_employee, make_sales_person
from sabaa.sabaa.doctype.commission_assignment.commission_assignment import get_assignments
from sabaa.sabaa.doctype.commission_plan.test_commission_plan import make_plan

SHARES = [{"share_name": "Drivers", "percent": 60}, {"share_name": "Workers", "percent": 40}]


class TestCommissionAssignment(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_commission_assignment"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))
		plan = make_plan("Test Assignment Plan", "2026-01-01", None, status="Draft")
		self.rule = frappe.get_doc(
			{
				"doctype": "Commission Rule",
				"plan": plan.name,
				"rule_name": "Pool",
				"category": "Logistics",
				"recipient_source": "Pool",
				"is_waiting_for_business": 1,
				"shares": SHARES,
			}
		).insert()
		self.employee = make_employee("Test Assignment Employee")
		self.sales_person = make_sales_person("Test Assignment Salesman", self.employee)

	def make_assignment(self, **overrides):
		values = {
			"doctype": "Commission Assignment",
			"rule": self.rule.name,
			"employee": self.employee,
			"assignment_type": "Exclude",
			"from_date": "2026-04-15",
		}
		values.update(overrides)
		return frappe.get_doc(values)

	def get_assignments(self, start: str, end: str, **kwargs):
		return get_assignments(self.rule.name, getdate(start), getdate(end), **kwargs)

	def test_open_ended_row_overlaps_later_month(self):
		row = self.make_assignment().insert()
		found = self.get_assignments("2026-05-01", "2026-05-31")
		self.assertEqual([item.name for item in found], [row.name])

	def test_row_that_ended_before_range_is_not_returned(self):
		self.make_assignment(to_date="2026-04-30").insert()
		self.assertEqual(self.get_assignments("2026-05-01", "2026-05-31"), [])

	def test_row_that_starts_after_range_is_not_returned(self):
		self.make_assignment(from_date="2026-06-01").insert()
		self.assertEqual(self.get_assignments("2026-05-01", "2026-05-31"), [])

	def test_filter_by_assignment_type(self):
		self.make_assignment().insert()
		self.assertEqual(self.get_assignments("2026-05-01", "2026-05-31", assignment_type="Include"), [])

	def test_assistant_of_needs_target_sales_person(self):
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_assignment(assignment_type="Assistant Of").insert()
		self.assertEqual(str(raised.exception), "Choose the salesman this assistant works with.")
		self.make_assignment(assignment_type="Assistant Of", target_sales_person=self.sales_person).insert()

	def test_share_member_must_name_a_share_of_the_rule(self):
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_assignment(assignment_type="Share Member", share_name="Cleaners").insert()
		self.assertEqual(
			str(raised.exception), "Cleaners is not a share of rule {0}. Choose one of: Drivers, Workers.".format(self.rule.name)
		)
		self.make_assignment(assignment_type="Share Member", share_name="Drivers").insert()

	def test_pool_share_percent_needs_percent(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_assignment(assignment_type="Pool Share %").insert()
		self.make_assignment(assignment_type="Pool Share %", percent=50).insert()

	def test_to_date_before_from_date_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_assignment(to_date="2026-04-01").insert()
