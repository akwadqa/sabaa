# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, flt, getdate

from sabaa.sabaa.commission.basis import format_month
from sabaa.sabaa.commission.constants import LineStatus
from sabaa.sabaa.commission.periods import month_start

DRAFT, CALCULATED, APPROVED, PAID, CANCELLED = "Draft", "Calculated", "Approved", "Paid", "Cancelled"
BLOCKING_STATUSES = (str(LineStatus.NEEDS_SETUP), str(LineStatus.MISSING_DATA))


class CommissionRun(Document):
	def validate(self) -> None:
		self.month = month_start(getdate(self.month))
		self.validate_plan_is_active()
		self.validate_unique_month()
		if self.docstatus == 0:
			self.status = CALCULATED if self.lines else DRAFT

	def validate_plan_is_active(self) -> None:
		from sabaa.sabaa.doctype.commission_plan.commission_plan import CommissionPlan

		self.company = frappe.db.get_value("Commission Plan", self.plan, "company")
		if CommissionPlan.get_active_plan(self.company, self.month) != self.plan:
			frappe.throw(_("Plan {0} is not the active plan for {1}.").format(self.plan, format_month(self.month)))

	def validate_unique_month(self) -> None:
		other = frappe.db.get_value(
			"Commission Run",
			{"company": self.company, "month": self.month, "docstatus": ("<", 2), "name": ("!=", self.name)},
		)
		if other:
			frappe.throw(_("Run {0} already covers {1} for this company.").format(other, format_month(self.month)))

	@frappe.whitelist()
	def calculate(self) -> None:
		if self.docstatus != 0:
			frappe.throw(_("Only a draft run can be calculated."))
		from sabaa.sabaa.commission.engine import CommissionEngine

		self.set("lines", [to_run_line(line) for line in CommissionEngine(self.plan, self.month).calculate()])
		self.set_totals()
		self.save()

	def set_totals(self) -> None:
		assigned = [row for row in self.lines if row.employee and row.status != str(LineStatus.NOT_ASSIGNED)]
		self.total_amount = flt(sum(flt(row.amount) for row in assigned), 2)
		self.not_assigned_amount = flt(sum(flt(row.amount) for row in self.lines) - self.total_amount, 2)
		self.employee_count = len({row.employee for row in assigned})

	def before_submit(self) -> None:
		if not self.lines:
			frappe.throw(_("Calculate the run before approval."))
		if any(row.status in BLOCKING_STATUSES for row in self.lines):
			frappe.throw(_("Fix the setup problems before approval."))

	def on_submit(self) -> None:
		self.db_set("status", APPROVED)

	def on_cancel(self) -> None:
		self.db_set("status", CANCELLED)

	@frappe.whitelist()
	def mark_paid(self, journal_entry: str | None = None) -> None:
		frappe.has_permission("Commission Run", "submit", self, throw=True)
		if self.status != APPROVED:
			frappe.throw(_("Only an approved run can be marked paid."))
		self.db_set({"status": PAID, "journal_entry": journal_entry})

	@frappe.whitelist()
	def get_live_difference(self) -> float:
		from sabaa.sabaa.commission.engine import CommissionEngine

		live = [to_run_line(line) for line in CommissionEngine(self.plan, self.month).calculate()]
		live_total = sum(flt(row["amount"]) for row in live if row["employee"] and row["status"] != str(LineStatus.NOT_ASSIGNED))
		return flt(live_total - flt(self.total_amount), 2)


def to_run_line(line) -> dict:
	values = line.as_dict()
	month_values = values.pop("month_values")
	values["month_values_text"] = ", ".join(f"{month}: {'—' if value is None else value}" for month, value in month_values.items())
	values["notes"] = "; ".join(values["notes"])
	return values


def get_locked_runs(plan: str) -> list[frappe._dict]:
	return frappe.get_all("Commission Run", filters={"plan": plan, "docstatus": 1}, fields=["name", "month"], order_by="month")


def is_month_locked(plan: str, month: date) -> str | None:
	month = month_start(getdate(month))
	return next((run.name for run in get_locked_runs(plan) if getdate(run.month) == month), None)


def get_covered_locked_runs(plan: str, start: date, end: date | None) -> set[tuple[str, date]]:
	"""Approved or paid runs whose payout month falls in start..end (an empty end has no end)."""
	start, end = getdate(start), getdate(end) if end else None
	return {
		(run.name, getdate(run.month))
		for run in get_locked_runs(plan)
		if month_start(start) <= getdate(run.month) and (end is None or getdate(run.month) <= end)
	}


def throw_locked(run_name: str, month: date) -> None:
	frappe.throw(_("{0} is approved for {1}.").format(run_name, format_month(month)))


def get_figure_lock(plan: str, rule: str, month: date) -> tuple[str, date] | None:
	"""An approved run that used this manual figure: it has lines for the rule (or a rule paired to it)
	and the figure's month is one of the run's basis months (the run month and the 2 before)."""
	month = month_start(getdate(month))
	rules = [rule, *frappe.get_all("Commission Rule", filters={"paired_rule": rule}, pluck="name")]
	run, line = frappe.qb.DocType("Commission Run"), frappe.qb.DocType("Commission Run Line")
	used = (
		frappe.qb.from_(run)
		.join(line)
		.on(line.parent == run.name)
		.where((run.plan == plan) & (run.docstatus == 1) & line.rule.isin(rules))
		.where(run.month[month : add_months(month, 2)])
		.select(run.name, run.month)
		.distinct()
		.orderby(run.month)
		.run(as_dict=True)
	)
	return (used[0].name, getdate(used[0].month)) if used else None
