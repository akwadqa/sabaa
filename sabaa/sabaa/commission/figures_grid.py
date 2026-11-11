"""The Missing months grid: manual figures for months before ERPNext, per rule and sales person."""

from datetime import date

import frappe
from frappe.utils import add_months, flt, getdate

from sabaa.sabaa.commission.periods import month_start
from sabaa.sabaa.commission.recipients import get_tree_members

AVERAGED = ("Quarterly Average", "Rolling 3-Month Average")


def get_missing_months() -> list[date]:
	"""The two months before ERPNext, which the first three-month averages need."""
	start = month_start(getdate(frappe.db.get_single_value("Commission Settings", "erpnext_start_date")))
	return [add_months(start, -2), add_months(start, -1)]


def get_missing_figure_grid(plan: str) -> dict:
	months = get_missing_months()
	rules = frappe.get_all(
		"Commission Rule",
		filters={"plan": plan, "period_mode": ("in", AVERAGED), "paired_rule": ("is", "not set")},
		fields=["name", "rule_name", "team_group", "recipient_source"],
		order_by="creation",
	)
	figures = frappe.get_all(
		"Commission Manual Figure", filters={"plan": plan}, fields=["rule", "sales_person", "month", "amount"]
	)
	values = {(f.rule, f.sales_person or None, getdate(f.month)): flt(f.amount) for f in figures}
	return {
		"months": [str(month) for month in months],
		"rules": [{"rule": rule.name, "rule_name": rule.rule_name, "rows": get_rows(rule, months, values)} for rule in rules],
	}


def get_rows(rule: frappe._dict, months: list[date], values: dict) -> list[dict]:
	if rule.team_group and rule.recipient_source != "Pool":
		people = [(m.sales_person, m.employee_name) for m in get_tree_members(rule.team_group, [], months[0], months[-1])]
		names = {m.sales_person for m in get_tree_members(rule.team_group, get_designations(rule.name), months[0], months[-1])}
		people = [(sp, label) for sp, label in people if sp in names] or people
	else:
		people = [(None, "Company")]
	return [
		{"sales_person": sp, "label": label, "values": {str(m): values.get((rule.name, sp, m)) for m in months}}
		for sp, label in people
	]


def get_designations(rule: str) -> list[str]:
	return frappe.get_all("Commission Designation", filters={"parent": rule}, pluck="designation")


def save_missing_figures(plan: str, rows: list[dict]) -> None:
	"""Rows: {rule, sales_person, month, amount}. An empty amount deletes the figure."""
	for row in map(frappe._dict, rows):
		filters = {"rule": row.rule, "month": month_start(getdate(row.month)), "sales_person": row.sales_person or ("is", "not set")}
		existing = frappe.db.get_value("Commission Manual Figure", filters)
		if row.amount in (None, ""):
			if existing:
				frappe.delete_doc("Commission Manual Figure", existing)
			continue
		doc = frappe.get_doc("Commission Manual Figure", existing) if existing else frappe.new_doc("Commission Manual Figure")
		doc.update({"rule": row.rule, "plan": plan, "month": row.month, "sales_person": row.sales_person, "amount": flt(row.amount)})
		doc.save()
