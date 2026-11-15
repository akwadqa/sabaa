# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

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
from sabaa.sabaa.doctype.commission_run.commission_run import is_month_locked


class TestCommissionRun(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_commission_run"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

		frappe.db.set_single_value("Commission Settings", "erpnext_start_date", "2026-05-01")
		frappe.db.set_value("Commission Plan", {"status": "Active"}, "status", "Draft")
		self.plan = make_plan("Test Run Plan", "2026-01-01", "2026-12-31").name
		self.employee = make_employee("Test Run Salesman")
		self.sales_person = make_sales_person("Test Run SP", self.employee)
		group = make_customer_group("Test Run Group")
		self.customer = make_customer("Test Run Customer", group)
		self.item = make_service_item("TEST-RUN-ITEM")
		self.rule = frappe.get_doc(
			{
				"doctype": "Commission Rule", "plan": self.plan, "rule_name": "Online", "category": "Smile24",
				"basis": "Net Invoiced Sales", "basis_sources": [{"customer_group": group, "measure": "Invoiced"}],
				"tiers": [{"threshold": 1000, "fixed_amount": 100}],
			}
		).insert()

	def make_run(self, month="2026-05-01"):
		return frappe.get_doc({"doctype": "Commission Run", "plan": self.plan, "month": month}).insert()

	def calculated_run(self):
		make_sales_invoice(self.customer, self.sales_person, "2026-05-05", [(self.item, 5000)])
		run = self.make_run()
		run.calculate()
		return run

	def test_status_flow(self):
		run = self.calculated_run()
		self.assertEqual((run.status, run.total_amount, run.employee_count), ("Calculated", 100, 1))

		run.submit()
		self.assertEqual(run.status, "Approved")
		run.mark_paid()
		self.assertEqual(frappe.db.get_value("Commission Run", run.name, "status"), "Paid")

		run.reload()
		self.assertRaisesRegex(frappe.ValidationError, "Only a draft run can be calculated.", run.calculate)

	def test_duplicate_month_refused(self):
		run = self.make_run()

		self.assertRaisesRegex(frappe.ValidationError, f"Run {run.name} already covers May 2026 for this company", self.make_run, "2026-05-20")

	def test_approval_refused_with_setup_problem(self):
		make_sales_invoice(self.customer, make_sales_person("Test Run Unlinked SP"), "2026-05-05", [(self.item, 5000)])
		run = self.make_run()
		run.calculate()

		self.assertRaisesRegex(frappe.ValidationError, "Fix the setup problems before approval.", run.submit)

	def test_rule_locked_after_approval_and_unlocked_by_cancel(self):
		run = self.calculated_run()
		run.submit()
		self.assertEqual(is_month_locked(self.plan, "2026-05-15"), run.name)

		self.rule.tiers[0].fixed_amount = 200
		self.assertRaisesRegex(frappe.ValidationError, f"Run {run.name} is approved. Copy the plan", self.rule.save)

		run.cancel()
		self.rule.reload()
		self.rule.tiers[0].fixed_amount = 200
		self.rule.save()

	def test_manual_figure_in_locked_period_refused(self):
		run = self.calculated_run()
		run.submit()
		figure = frappe.get_doc(
			{"doctype": "Commission Manual Figure", "rule": self.rule.name, "month": "2026-04-01", "amount": 10}
		)

		self.assertRaisesRegex(frappe.ValidationError, f"{run.name} is approved for May 2026.", figure.insert)

	def test_assignment_can_be_ended_after_an_approved_month(self):
		other = make_employee("Test Run Other")
		assignment = frappe.get_doc(
			{"doctype": "Commission Assignment", "rule": self.rule.name, "employee": other,
			 "assignment_type": "Exclude", "from_date": "2026-01-01"}
		).insert()
		run = self.calculated_run()
		run.submit()

		assignment.to_date = "2026-06-30"
		assignment.save()

		assignment.from_date = "2026-06-01"
		self.assertRaisesRegex(frappe.ValidationError, f"{run.name} is approved for May 2026.", assignment.save)

	def test_figure_of_a_rule_the_run_did_not_use_stays_editable(self):
		quarterly = frappe.get_doc(
			{"doctype": "Commission Rule", "plan": self.plan, "rule_name": "Quarterly", "category": "Smile24",
			 "period_mode": "Quarterly Average", "tiers": [{"threshold": 1000, "fixed_amount": 100}]}
		).insert()
		run = self.calculated_run()
		run.submit()

		frappe.get_doc(
			{"doctype": "Commission Manual Figure", "rule": quarterly.name, "month": "2026-04-01", "amount": 10}
		).insert()

	def test_unchanged_figure_can_be_saved_after_approval(self):
		figure = frappe.get_doc(
			{"doctype": "Commission Manual Figure", "rule": self.rule.name, "month": "2026-04-01", "amount": 10}
		).insert()
		run = self.calculated_run()
		run.submit()

		figure.save()
		figure.amount = 20
		self.assertRaisesRegex(frappe.ValidationError, f"{run.name} is approved for May 2026.", figure.save)

	def test_run_needs_the_active_plan(self):
		frappe.db.set_value("Commission Plan", self.plan, "status", "Draft")

		self.assertRaisesRegex(frappe.ValidationError, "Plan Test Run Plan is not the active plan for May 2026.", self.make_run)

	def test_overlapping_assignment_refused(self):
		other = make_employee("Test Run Twice")
		row = {"doctype": "Commission Assignment", "rule": self.rule.name, "employee": other, "assignment_type": "Include", "from_date": "2026-05-01"}
		frappe.get_doc(row).insert()

		self.assertRaisesRegex(frappe.ValidationError, "already has an overlapping Include row", frappe.get_doc(dict(row, from_date="2026-06-01")).insert)
