# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

from collections import defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_months, flt, getdate

from sabaa.sabaa.commission.basis import format_month
from sabaa.sabaa.commission.constants import Category, LineStatus
from sabaa.sabaa.commission.engine import CommissionEngine
from sabaa.sabaa.commission.lines import CommissionLine
from sabaa.sabaa.commission.periods import month_start
from sabaa.sabaa.commission.setup_check import SetupProblem, get_settings_problems
from sabaa.sabaa.doctype.commission_plan.commission_plan import CommissionPlan

SUMMARY, DETAIL, QUARTER = "Summary by Employee", "Detail", "Quarter"
NOT_ASSIGNED_LABEL = "Not assigned"


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	company = filters.company or frappe.db.get_single_value("Commission Settings", "company")
	months = get_months(filters)
	plan = filters.plan or CommissionPlan.get_active_plan(company, months[-1])
	if not plan:
		return [], [], _("No active commission plan covers {0}.").format(format_month(months[-1]))

	lines, problems = calculate(plan, months)
	message = get_run_banner(plan, months, lines) + get_message(problems)
	lines = [line for line in lines if matches(line, filters)]
	if filters.view == DETAIL:
		return get_detail_columns(), [get_detail_row(line) for line in lines], message
	return get_summary_columns(), get_summary_rows(lines), message


def get_run_banner(plan: str, months: list[date], lines: list[CommissionLine]) -> str:
	"""Warn when approved runs for these months paid a different total than the live figures."""
	runs = frappe.get_all(
		"Commission Run", filters={"plan": plan, "docstatus": 1, "month": ("in", months)}, fields=["name", "total_amount"]
	)
	if not runs:
		return ""
	live = sum(flt(line.amount) for line in lines if line.employee and line.status != LineStatus.NOT_ASSIGNED)
	approved = sum(flt(run.total_amount) for run in runs)
	difference = flt(live - approved, 2)
	if not difference:
		return ""
	names = ", ".join(run.name for run in runs)
	return f"<p><b>{_('Approved run {0} paid {1}. The live figures differ by {2} QAR.').format(names, frappe.format(approved, 'Currency'), frappe.format(difference, 'Currency'))}</b></p>"


def get_months(filters: frappe._dict) -> list[date]:
	if filters.period_type == QUARTER and filters.quarter:
		year, quarter = filters.quarter.split("-Q")
		first = date(int(year), (int(quarter) - 1) * 3 + 1, 1)
		return [add_months(first, offset) for offset in range(3)]
	return [month_start(getdate(filters.month))]


def calculate(plan: str, months: list[date]) -> tuple[list[CommissionLine], list[SetupProblem]]:
	lines, problems = [], []
	for month in months:
		engine = CommissionEngine(plan, month)
		lines.extend(engine.calculate())
		problems.extend(get_settings_problems(engine) + engine.problems)
	unique = {}
	for problem in problems:
		unique.setdefault((problem.rule, problem.message), problem)
	return lines, list(unique.values())


def matches(line: CommissionLine, filters: frappe._dict) -> bool:
	if filters.category and line.category != filters.category:
		return False
	return not filters.employee or line.employee == filters.employee


def get_summary_columns() -> list[dict]:
	columns = [
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 130},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
	]
	columns += [
		{"label": _(category), "fieldname": frappe.scrub(category), "fieldtype": "Currency", "width": 140}
		for category in Category
	]
	columns.append({"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 130})
	columns.append({"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 160})
	return columns


def get_summary_rows(lines: list[CommissionLine]) -> list[dict]:
	"""One row per employee; amounts that reach no employee go to a final Not assigned row."""
	rows: dict[str | None, dict] = {}
	for line in lines:
		key = line.employee if line.status != LineStatus.NOT_ASSIGNED else None
		row = rows.setdefault(key, new_summary_row(line, key))
		row[frappe.scrub(line.category)] += flt(line.amount)
		row["total"] += flt(line.amount)
		row["statuses"].add(str(line.status))

	ordered = sorted((row for key, row in rows.items() if key), key=lambda row: row["employee_name"] or "")
	if None in rows:
		ordered.append(rows[None])
	for row in ordered:
		row["status"] = worst_status(row.pop("statuses"))
	return ordered


def new_summary_row(line: CommissionLine, key: str | None) -> dict:
	row = {"employee": key, "employee_name": line.employee_name if key else _(NOT_ASSIGNED_LABEL), "total": 0, "statuses": set()}
	row.update({frappe.scrub(category): 0 for category in Category})
	return row


STATUS_ORDER = [LineStatus.MISSING_DATA, LineStatus.NEEDS_SETUP, LineStatus.NOT_ASSIGNED, LineStatus.WAITING, LineStatus.READY]


def worst_status(statuses: set[str]) -> str:
	return next((str(status) for status in STATUS_ORDER if str(status) in statuses), str(LineStatus.READY))


def get_detail_columns() -> list[dict]:
	def column(label, fieldname, fieldtype="Data", width=120, options=None):
		return {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width, "options": options}

	return [
		column("Employee", "employee", "Link", 120, "Employee"),
		column("Employee Name", "employee_name", width=180),
		column("Sales Person", "sales_person", "Link", 160, "Sales Person"),
		column("Category", "category", width=130),
		column("Rule", "rule", "Link", 200, "Commission Rule"),
		column("Role / Share", "role", width=150),
		column("Basis", "basis_label", width=130),
		column("Months", "months", width=260),
		column("Average", "basis_amount", "Currency"),
		column("Target", "target", "Currency"),
		column("Tier", "tier_label", width=100),
		column("Next Target", "next_target", "Currency"),
		column("Gap", "gap_to_next", "Currency"),
		column("Fixed", "fixed_part", "Currency"),
		column("Excess", "excess_part", "Currency"),
		column("Share %", "share_percent", "Percent", 90),
		column("Amount", "amount", "Currency", 130),
		column("Status", "status", width=160),
		column("Notes", "notes", width=300),
	]


def get_detail_row(line: CommissionLine) -> dict:
	row = line.as_dict()
	row["role"] = line.share_name or line.role_label
	row["months"] = ", ".join(f"{month}: {'—' if value is None else frappe.format(value, 'Float')}" for month, value in line.month_values.items())
	row["notes"] = "; ".join(line.notes)
	row.pop("month_values")
	return row


def get_message(problems: list[SetupProblem]) -> str:
	if not problems:
		return ""
	items = "".join(f"<li>{frappe.utils.escape_html(p.message)} → {get_fix_link(p)}</li>" for p in problems)
	return f"<div><b>{_('Setup problems')}</b><ul>{items}</ul></div>"


def get_fix_link(problem: SetupProblem) -> str:
	fix = problem.fix or {}
	if fix.get("doctype"):
		route = f"/app/{frappe.scrub(fix['doctype']).replace('_', '-')}/{fix['name']}"
	else:
		route = "/app/commission-setup"
	return f'<a href="{route}">{_("Fix")}</a>'
