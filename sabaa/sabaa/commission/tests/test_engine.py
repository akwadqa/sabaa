# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from sabaa.sabaa.commission.api import preview_tier
from sabaa.sabaa.commission.constants import LineStatus
from sabaa.sabaa.commission.engine import CommissionEngine
from sabaa.sabaa.commission.setup_check import check_setup
from sabaa.sabaa.commission.sources import BasisRow, DeliveryRow
from sabaa.sabaa.commission.tests.factories import make_employee, make_plan, make_sales_person

MAY = getdate("2026-05-01")
SALESPERSON_TIERS = [(70000, 200, 0), (84000, 367, 0), (105000, 1050, 0), (131250, 2362.5, 0), (157500, 3937.5, 3.5)]


class FakeReader:
	def __init__(self, rows=(), delivery=()):
		self.rows, self.delivery = list(rows), list(delivery)

	def get_basis_rows(self, rule, from_date, to_date):
		return [row for row in self.rows if from_date <= row.month <= to_date]

	def get_delivery_rows(self, rule, from_date, to_date):
		return self.delivery


def ensure_designation(name: str) -> str:
	if not frappe.db.exists("Designation", name):
		frappe.get_doc({"doctype": "Designation", "designation_name": name}).insert()
	return name


class TestEngine(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_engine"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

		frappe.db.set_single_value("Commission Settings", "erpnext_start_date", "2026-05-01")
		self.plan = make_plan("Test Engine Plan", "2026-01-01", "2026-12-31", "Draft").name
		self.employee = make_employee("Test Engine Salesman")
		self.sales_person = make_sales_person("Test Engine SP", self.employee)

	def make_rule(self, rule_name, **fields):
		values = {"doctype": "Commission Rule", "plan": self.plan, "rule_name": rule_name, "category": "Traditional Trade"}
		values.update(fields)
		return frappe.get_doc(values).insert().name

	def tiers(self, rows):
		return [{"threshold": t, "fixed_amount": f, "excess_percent": e} for t, f, e in rows]

	def salesperson_rule(self, period_mode="Rolling 3-Month Average"):
		return self.make_rule("Cash Salesperson", period_mode=period_mode, tiers=self.tiers(SALESPERSON_TIERS))

	def figure(self, rule, month, amount, sales_person=None):
		frappe.get_doc(
			{"doctype": "Commission Manual Figure", "rule": rule, "month": month, "sales_person": sales_person or self.sales_person, "amount": amount}
		).insert()

	def run_engine(self, rule, rows=(), delivery=()):
		return CommissionEngine(self.plan, MAY, FakeReader(rows, delivery)).calculate_rule(rule)

	def test_rolling_average_with_manual_months(self):
		rule = self.salesperson_rule()
		self.figure(rule, "2026-03-01", 60000)
		self.figure(rule, "2026-04-01", 90000)

		(line,) = self.run_engine(rule, [BasisRow(MAY, self.sales_person, 120000)])

		self.assertEqual((line.basis_amount, line.tier_label, line.amount), (90000, "2 of 5", 367))
		self.assertEqual((line.employee, line.status), (self.employee, LineStatus.READY))

	def test_missing_manual_month(self):
		rule = self.salesperson_rule()
		self.figure(rule, "2026-03-01", 60000)

		(line,) = self.run_engine(rule, [BasisRow(MAY, self.sales_person, 120000)])

		self.assertEqual((line.status, line.amount), (LineStatus.MISSING_DATA, 0))
		self.assertIn("April 2026", " ".join(line.notes))

	def test_month_without_activity_counts_as_zero(self):
		rule = self.salesperson_rule()
		self.figure(rule, "2026-03-01", 60000)
		self.figure(rule, "2026-04-01", 90000)

		(line,) = self.run_engine(rule)

		self.assertEqual(line.month_values["May 2026"], 0)
		self.assertEqual((line.status, line.basis_amount), (LineStatus.READY, 50000))

	def test_waiting_rule(self):
		rule = self.make_rule("Logistics Team", category="Logistics", is_waiting_for_business=1, status_note="Logistics tiers not given (L1)")

		(line,) = self.run_engine(rule)

		self.assertEqual((line.status, line.notes), (LineStatus.WAITING, ["Logistics tiers not given (L1)"]))

	def test_company_sales_pool_split_manager_assistant(self):
		head, manager = ensure_designation("Test Sales Head"), ensure_designation("Test Sales Manager")
		make_employee("Test Head", head)
		make_employee("Test Manager", manager)
		rule = self.make_rule(
			"Manager Pool",
			category="Sales Management",
			basis="Company Sales",
			recipient_source="Pool",
			tiers=self.tiers([(1500000, 2000, 0), (1600000, 2000, 2)]),
			shares=[
				{"share_name": "Manager", "percent": 60, "designation": head, "split": "Equal"},
				{"share_name": "Assistant", "percent": 40, "designation": manager, "split": "Equal"},
			],
		)

		lines = self.run_engine(rule, [BasisRow(MAY, None, 900000), BasisRow(MAY, "X", 750000)])

		self.assertEqual([(line.share_name, line.amount) for line in lines], [("Manager", 1800), ("Assistant", 1200)])
		self.assertEqual(lines[0].basis_amount, 1650000)

	def test_smile24_driver(self):
		driver_employee = make_employee("Test Smile Driver")
		rule = self.make_rule(
			"Smile24 Drivers", category="Smile24", basis="Delivery Fees", attribute_by="Invoice Driver",
			tier_method="Flat Rate", flat_rate_percent=50, bonus_after_count=100, bonus_per_unit=5,
		)

		(line,) = self.run_engine(rule, delivery=[DeliveryRow(MAY, "DRV-1", driver_employee, 1500, 130)])

		self.assertEqual((line.employee, line.amount), (driver_employee, 900))

	def test_logistics_targets_scale_with_drivers(self):
		driver, worker = ensure_designation("Test Logistics Driver"), ensure_designation("Test Logistics Worker")
		for n in range(9):
			make_employee(f"Test Driver {n}", driver)
		for n in range(2):
			make_employee(f"Test Worker {n}", worker)
		rule = self.make_rule(
			"Logistics", category="Logistics", basis="Company Sales", recipient_source="Pool",
			tiers=self.tiers([(800000, 5000, 0)]), headcount_base=8, headcount_share="Drivers",
			shares=[
				{"share_name": "Drivers", "percent": 60, "designation": driver, "split": "Equal"},
				{"share_name": "Workers", "percent": 40, "designation": worker, "split": "Equal"},
			],
		)

		below = self.run_engine(rule, [BasisRow(MAY, None, 850000)])
		reached = self.run_engine(rule, [BasisRow(MAY, None, 900000)])

		self.assertEqual(sum(line.amount for line in below), 0)
		totals = {}
		for line in reached:
			totals[line.share_name] = totals.get(line.share_name, 0) + line.amount
		self.assertEqual(totals, {"Drivers": 3000, "Workers": 2000})

	def test_preview_matches_engine(self):
		rule = self.salesperson_rule("Monthly")

		(line,) = self.run_engine(rule, [BasisRow(MAY, self.sales_person, 120000)])

		self.assertEqual(preview_tier(rule, 120000)["amount"], line.amount)
		self.assertEqual(preview_tier(rule, 120000)["text"], "120,000 → Tier 3 of 5 → 1,050 QAR")

	def test_setup_check_names_sales_person_without_employee(self):
		make_sales_person("Prabhu Test")
		self.salesperson_rule("Monthly")

		problems = check_setup(self.plan, MAY, FakeReader([BasisRow(MAY, "Prabhu Test", 1000)]))

		problem = next(p for p in problems if p.message == "Sales Person Prabhu Test has no employee.")
		self.assertEqual(problem.fix, {"doctype": "Sales Person", "name": "Prabhu Test"})

	def test_real_sources_net_invoiced(self):
		from sabaa.sabaa.commission.tests.factories import (
			make_customer,
			make_customer_group,
			make_sales_invoice,
			make_service_item,
		)

		group = make_customer_group("Test Engine Group")
		customer = make_customer("Test Engine Customer", group)
		make_sales_invoice(customer, self.sales_person, "2026-05-12", [(make_service_item("TEST-ENGINE-ITEM"), 120000)])
		rule = self.make_rule(
			"Online Salesperson", category="Smile24", basis="Net Invoiced Sales",
			basis_sources=[{"customer_group": group, "measure": "Invoiced"}], tiers=self.tiers(SALESPERSON_TIERS),
		)

		(line,) = CommissionEngine(self.plan, MAY).calculate_rule(rule)

		self.assertEqual((line.basis_amount, line.amount, line.employee), (120000, 1050, self.employee))

	def test_non_member_sales_does_not_ask_for_figures(self):
		team = make_sales_person("Test Engine Team", is_group=1)
		make_sales_person("Test Engine Member", make_employee("Test Engine Member Emp"), team)
		rule = self.make_rule(
			"Team Salesperson", period_mode="Rolling 3-Month Average", tiers=self.tiers(SALESPERSON_TIERS), team_group=team
		)

		lines = self.run_engine(rule, [BasisRow(MAY, self.sales_person, 5000)])
		outsider = next(line for line in lines if line.sales_person == self.sales_person)
		problems = CommissionEngine(self.plan, MAY, FakeReader([BasisRow(MAY, self.sales_person, 5000)]))
		problems.calculate_rule(rule)

		self.assertEqual(outsider.status, LineStatus.NOT_ASSIGNED)
		self.assertFalse([p for p in problems.problems if self.sales_person in p.message])

	def test_delivery_without_driver(self):
		rule = self.make_rule(
			"Smile24 Drivers", category="Smile24", basis="Delivery Fees", attribute_by="Invoice Driver",
			tier_method="Flat Rate", flat_rate_percent=50,
		)
		engine = CommissionEngine(self.plan, MAY, FakeReader(delivery=[DeliveryRow(MAY, None, None, 30, 2)]))

		(line,) = engine.calculate_rule(rule)

		self.assertEqual((line.status, line.amount), (LineStatus.NOT_ASSIGNED, 15))
		self.assertEqual([p.message for p in engine.problems], ["Smile24 Drivers: some delivery invoices have no driver."])
