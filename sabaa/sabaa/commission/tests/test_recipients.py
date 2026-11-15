# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from sabaa.sabaa.commission.recipients import (
	apply_overrides,
	get_designation_members,
	get_group_supervisors,
	get_tree_members,
)
from sabaa.sabaa.commission.tests.factories import make_employee, make_plan, make_sales_person

MAY = (getdate("2026-05-01"), getdate("2026-05-31"))
JUNE = (getdate("2026-06-01"), getdate("2026-06-30"))


class TestRecipients(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_recipients"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

		for designation in ("Salesman", "Sales Head", "Sales Supervisor"):
			if not frappe.db.exists("Designation", designation):
				frappe.get_doc({"doctype": "Designation", "designation_name": designation}).insert()
		self.group = make_sales_person("Test Cash Group", is_group=1)
		self.salesman = make_employee("Test Salesman One", "Salesman")
		self.salesman_sp = make_sales_person("Test Salesman One SP", self.salesman, self.group)

	def members(self, period=MAY, designations=("Salesman",)):
		return get_tree_members(self.group, list(designations), *period)

	def test_tree_members_filtered_by_designation(self):
		head = make_employee("Test Sales Head", "Sales Head")
		make_sales_person("Test Sales Head SP", head, self.group)

		self.assertEqual([m.employee for m in self.members()], [self.salesman])
		self.assertEqual(self.members()[0].source, "From HR tree")

	def test_leaf_without_employee_is_returned(self):
		make_sales_person("Test Unlinked SP", None, self.group)

		unlinked = [m for m in self.members() if m.sales_person == "Test Unlinked SP"]
		self.assertEqual(len(unlinked), 1)
		self.assertIsNone(unlinked[0].employee)

	def test_relieved_employee_eligible_until_relieving_month(self):
		leaver = make_employee("Test Leaver", "Salesman", status="Left", relieving_date="2026-05-10")
		make_sales_person("Test Leaver SP", leaver, self.group)

		self.assertIn(leaver, [m.employee for m in self.members(MAY)])
		self.assertNotIn(leaver, [m.employee for m in self.members(JUNE)])

	def test_group_supervisors(self):
		supervisor = make_employee("Test Supervisor", "Sales Supervisor")
		sub_group = make_sales_person("Test Cash Sub Group", supervisor, self.group, is_group=1)

		self.assertEqual(get_group_supervisors(self.group), {sub_group: supervisor})

	def test_designation_members(self):
		self.assertIn(self.salesman, [m.employee for m in get_designation_members("Salesman", None, *MAY)])

	def test_exclude_applies_only_within_its_dates(self):
		plan = make_plan("Test Recipient Plan", "2026-01-01", "2026-12-31", "Draft")
		rule = frappe.get_doc(
			{
				"doctype": "Commission Rule",
				"plan": plan.name,
				"rule_name": "Cash Salesperson",
				"category": "Traditional Trade",
				"is_waiting_for_business": 1,
			}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Commission Assignment",
				"rule": rule.name,
				"employee": self.salesman,
				"assignment_type": "Exclude",
				"from_date": "2026-06-01",
			}
		).insert()

		self.assertEqual(len(apply_overrides(self.members(MAY), rule.name, *MAY)), 1)
		self.assertEqual(apply_overrides(self.members(JUNE), rule.name, *JUNE), [])
