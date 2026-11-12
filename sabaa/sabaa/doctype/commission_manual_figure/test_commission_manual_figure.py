# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from sabaa.sabaa.commission.tests.factories import make_plan, make_sales_person
from sabaa.sabaa.doctype.commission_manual_figure.commission_manual_figure import get_manual_figures


class TestCommissionManualFigure(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_commission_manual_figure"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))
		frappe.db.set_single_value("Commission Settings", "erpnext_start_date", "2026-05-01")
		self.plan = make_plan("Test Figure Plan", "2026-01-01", None, status="Draft")
		self.rule = frappe.get_doc(
			{
				"doctype": "Commission Rule",
				"plan": self.plan.name,
				"rule_name": "Salesperson",
				"category": "Traditional Trade",
				"tier_method": "Flat Rate",
				"flat_rate_percent": 1,
			}
		).insert()
		self.sales_person = make_sales_person("Test Figure Salesman")

	def make_figure(self, month: str = "2026-03-17", **overrides):
		values = {
			"doctype": "Commission Manual Figure",
			"plan": self.plan.name,
			"rule": self.rule.name,
			"month": month,
			"amount": 1000,
		}
		values.update(overrides)
		return frappe.get_doc(values)

	def test_month_is_normalised_to_first_of_month(self):
		self.assertEqual(self.make_figure().insert().month, getdate("2026-03-01"))

	def test_month_in_erpnext_is_refused(self):
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_figure("2026-05-01").insert()
		self.assertEqual(
			str(raised.exception), "May 2026 is in ERPNext. Manual figures are only for months before 2026-05-01."
		)

	def test_duplicate_figure_is_refused(self):
		self.make_figure().insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_figure("2026-03-01").insert()

	def test_duplicate_rule_level_figure_is_refused_but_person_figure_is_allowed(self):
		self.make_figure().insert()
		self.make_figure(sales_person=self.sales_person).insert()
		with self.assertRaises(frappe.ValidationError):
			self.make_figure(sales_person=self.sales_person).insert()

	def test_saving_an_existing_figure_is_not_a_duplicate(self):
		figure = self.make_figure().insert()
		figure.amount = 2000
		figure.save()

	def test_get_manual_figures_keys_by_month_and_person(self):
		self.make_figure(amount=1000).insert()
		self.make_figure(sales_person=self.sales_person, amount=400).insert()
		figures = get_manual_figures(self.rule.name, [getdate("2026-03-01"), getdate("2026-04-01")])
		self.assertEqual(
			figures, {(getdate("2026-03-01"), None): 1000, (getdate("2026-03-01"), self.sales_person): 400}
		)

	def test_get_manual_figures_without_months_is_empty(self):
		self.assertEqual(get_manual_figures(self.rule.name, []), {})

	def test_missing_erpnext_start_date_is_refused(self):
		frappe.db.set_single_value("Commission Settings", "erpnext_start_date", None)
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_figure().insert()
		self.assertEqual(str(raised.exception), "Set the ERPNext Start Date in Commission Settings.")

	def test_plan_must_match_the_rules_plan(self):
		other = make_plan("Test Other Plan", "2026-01-01", None, status="Draft")
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_figure(plan=other.name).insert()
		self.assertEqual(
			str(raised.exception), "Rule {0} belongs to plan {1}.".format(self.rule.name, self.plan.name)
		)

	def test_plan_is_filled_from_the_rule(self):
		figure = self.make_figure(plan=None)
		figure.flags.ignore_mandatory = True
		self.assertEqual(figure.insert().plan, self.plan.name)
