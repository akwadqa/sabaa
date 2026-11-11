# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from sabaa.sabaa.commission.tiers import Tier, validate_tiers

COMPANY = "Saba Trading Group"
TIERS = [(70000, 200, 0), (84000, 367, 0), (105000, 1050, 0), (131250, 2362.5, 0), (157500, 3937.5, 3.5)]


class TestCommissionRule(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_commission_rule"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))
		self.plan = frappe.get_doc(
			{
				"doctype": "Commission Plan",
				"plan_name": "Test Rule Plan",
				"company": COMPANY,
				"valid_from": "2026-01-01",
				"status": "Draft",
			}
		).insert()

	def make_rule(self, tiers=TIERS, **overrides):
		values = {
			"doctype": "Commission Rule",
			"plan": self.plan.name,
			"rule_name": "Salesperson",
			"category": "Traditional Trade",
			"basis": "Collected Sales",
			"period_mode": "Rolling 3-Month Average",
			"tier_method": "Tiered",
			"tiers": [
				{"threshold": threshold, "fixed_amount": fixed, "excess_percent": excess}
				for threshold, fixed, excess in tiers
			],
		}
		values.update(overrides)
		return frappe.get_doc(values)

	def test_rule_is_named_from_plan_and_rule_name(self):
		self.assertEqual(self.make_rule().insert().name, "Test Rule Plan-Salesperson")

	def test_rule_rejects_unordered_tiers(self):
		unordered = [(84000, 367, 0), (70000, 200, 0)]
		expected = validate_tiers([Tier(*row) for row in unordered])[0]
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_rule(unordered).insert()
		self.assertEqual(str(raised.exception), expected)

	def test_pool_shares_must_total_100(self):
		rule = self.make_rule(
			recipient_source="Pool",
			shares=[{"share_name": "Drivers", "percent": 60}, {"share_name": "Workers", "percent": 35}],
		)
		with self.assertRaises(frappe.ValidationError) as raised:
			rule.insert()
		self.assertEqual(str(raised.exception), "Shares total 95%. They must total 100%.")

	def test_pool_shares_totalling_100_are_saved(self):
		rule = self.make_rule(
			recipient_source="Pool",
			shares=[{"share_name": "Drivers", "percent": 60}, {"share_name": "Workers", "percent": 40}],
		)
		rule.insert()

	def test_summary_is_filled(self):
		rule = self.make_rule().insert()
		self.assertEqual(rule.summary, "5 tiers · Rolling 3-Month Average · Collected Sales")

	def test_waiting_rule_may_have_no_tiers(self):
		with self.assertRaises(frappe.ValidationError) as raised:
			self.make_rule(tiers=[]).insert()
		self.assertEqual(
			str(raised.exception), "Add at least one tier, or tick Waiting for business input."
		)
		self.make_rule(tiers=[], is_waiting_for_business=1).insert()

	def test_get_tiers_returns_tier_objects(self):
		rule = self.make_rule().insert()
		self.assertEqual(rule.get_tiers()[-1], Tier(157500, 3937.5, 3.5))
