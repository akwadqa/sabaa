"""Who a rule pays in a month, and the hand-made changes the People dialog saves as assignments."""

from datetime import date

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from sabaa.sabaa.commission.periods import month_end, month_start
from sabaa.sabaa.commission.recipients import (
	Member,
	get_designation_members,
	get_hand_added_member,
	get_tree_members,
)
from sabaa.sabaa.commission.tiers import format_number
from sabaa.sabaa.doctype.commission_assignment.commission_assignment import get_assignments

EXCLUDE, INCLUDE, POOL_SHARE, ASSISTANT_OF = "Exclude", "Include", "Pool Share %", "Assistant Of"


def get_people(rule_name: str, month: date | str) -> list[dict]:
	rule = frappe.get_doc("Commission Rule", rule_name)
	start, end = month_start(getdate(month)), month_end(getdate(month))
	excluded = {row.employee for row in get_assignments(rule.name, start, end, EXCLUDE)}
	percents = {row.employee: flt(row.percent) for row in get_assignments(rule.name, start, end, POOL_SHARE)}
	assistants = {row.employee: row.target_sales_person for row in get_assignments(rule.name, start, end, ASSISTANT_OF)}

	members = get_base_members(rule, start, end)
	members += [get_hand_added_member(row.employee) for row in get_assignments(rule.name, start, end, INCLUDE)]
	known = {member.employee for member in members}
	members += [get_hand_added_member(e) for e in list(percents) + list(assistants) if e not in known]

	seen, people = set(), []
	for member in members:
		if member.employee in seen:
			continue
		seen.add(member.employee)
		people.append(
			{
				**member.__dict__,
				"excluded": member.employee in excluded,
				"percent": percents.get(member.employee),
				"assistant_of": assistants.get(member.employee),
			}
		)
	return people


def get_base_members(rule, start: date, end: date) -> list[Member]:
	designations = [row.designation for row in rule.member_designations]
	members = get_tree_members(rule.team_group, designations, start, end) if rule.team_group else []
	for share in rule.shares:
		if share.designation:
			members += get_designation_members(share.designation, share.department, start, end)
	return members


def save_people(rule_name: str, month: date | str, rows: list[dict]) -> None:
	"""Rows: {employee, exclude?, percent?, assistant_of?}. Changes start on the first day of `month`."""
	start = month_start(getdate(month))
	rows = [frappe._dict(row) for row in rows]
	validate_percents(rows)
	for row in rows:
		if "exclude" in row:
			set_exclusion(rule_name, row.employee, bool(row.exclude), start)
		if row.get("percent") is not None:
			replace_assignment(rule_name, row.employee, POOL_SHARE, start, percent=flt(row.percent))
		if row.get("assistant_of"):
			replace_assignment(rule_name, row.employee, ASSISTANT_OF, start, target_sales_person=row.assistant_of)


def validate_percents(rows: list[frappe._dict]) -> None:
	percents = [flt(row.percent) for row in rows if row.get("percent") is not None]
	if percents and flt(sum(percents), 2) != 100:
		frappe.throw(_("Shares total {0}%. They must total 100%.").format(format_number(sum(percents))))


def set_exclusion(rule: str, employee: str, is_excluded: bool, start: date) -> None:
	current = [row for row in get_assignments(rule, start, month_end(start), EXCLUDE) if row.employee == employee]
	if is_excluded and not current:
		insert_assignment(rule, employee, EXCLUDE, start)
	elif not is_excluded:
		for row in current:
			end_assignment(row, start)


def replace_assignment(rule: str, employee: str, assignment_type: str, start: date, **values) -> None:
	current = [row for row in get_assignments(rule, start, month_end(start), assignment_type) if row.employee == employee]
	if any(all(row.get(key) == value for key, value in values.items()) for row in current):
		return
	for row in current:
		end_assignment(row, start)
	insert_assignment(rule, employee, assignment_type, start, **values)


def insert_assignment(rule: str, employee: str, assignment_type: str, start: date, **values) -> None:
	frappe.get_doc(
		{"doctype": "Commission Assignment", "rule": rule, "employee": employee,
		 "assignment_type": assignment_type, "from_date": start, **values}
	).insert()


def end_assignment(row: frappe._dict, start: date) -> None:
	"""Stop an assignment before `start`; one that only begins there is removed."""
	if getdate(row.from_date) >= start:
		frappe.delete_doc("Commission Assignment", row.name)
	else:
		doc = frappe.get_doc("Commission Assignment", row.name)
		doc.to_date = add_days(start, -1)
		doc.save()
