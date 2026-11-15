"""Who a commission rule pays: Sales Person tree members, designation holders and dated overrides."""

from dataclasses import dataclass
from datetime import date

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull

from sabaa.sabaa.doctype.commission_assignment.commission_assignment import get_assignments

FROM_HR_TREE = "From HR tree"
BY_DESIGNATION = "By designation"
ADDED_BY_HAND = "Added by hand"

SalesPerson = DocType("Sales Person")
Employee = DocType("Employee")


@dataclass(frozen=True)
class Member:
	employee: str | None
	employee_name: str
	sales_person: str | None
	designation: str | None
	source: str


def get_tree_members(group: str, designations: list[str], start: date, end: date) -> list[Member]:
	"""Enabled leaf Sales Persons under `group`; leaves without an employee are kept (Needs setup).

	An empty `designations` list accepts every designation.
	"""
	root = DocType("Sales Person").as_("root")
	rows = (
		frappe.qb.from_(SalesPerson)
		.join(root)
		.on((SalesPerson.lft > root.lft) & (SalesPerson.rgt < root.rgt))
		.left_join(Employee)
		.on(Employee.name == SalesPerson.employee)
		.where((root.name == group) & (SalesPerson.is_group == 0) & (SalesPerson.enabled == 1))
		.select(
			SalesPerson.name.as_("sales_person"),
			Employee.name.as_("employee"),
			Employee.employee_name,
			Employee.designation,
			Employee.status,
			Employee.relieving_date,
			Employee.date_of_joining,
		)
		.orderby(SalesPerson.lft)
		.run(as_dict=True)
	)
	return [
		Member(row.employee, row.employee_name or row.sales_person, row.sales_person, row.designation, FROM_HR_TREE)
		for row in rows
		if not row.employee or ((not designations or row.designation in designations) and is_eligible(row, start, end))
	]


def is_eligible(employee: frappe._dict, start: date, end: date) -> bool:
	"""Active, or relieved on or after the period start; and joined by the period end."""
	if employee.date_of_joining and employee.date_of_joining > end:
		return False
	return employee.status == "Active" or bool(employee.relieving_date and employee.relieving_date >= start)


def get_group_supervisors(group: str) -> dict[str, str]:
	"""Group node -> its `employee`, for `group` and every group node under it that has one."""
	root = DocType("Sales Person").as_("root")
	rows = (
		frappe.qb.from_(SalesPerson)
		.join(root)
		.on((SalesPerson.lft >= root.lft) & (SalesPerson.rgt <= root.rgt))
		.where((root.name == group) & (SalesPerson.is_group == 1) & (IfNull(SalesPerson.employee, "") != ""))
		.select(SalesPerson.name, SalesPerson.employee)
		.run(as_dict=True)
	)
	return {row.name: row.employee for row in rows}


def get_designation_members(designation: str, department: str | None, start: date, end: date) -> list[Member]:
	filters = {"designation": designation}
	if department:
		filters["department"] = department
	employees = frappe.get_all(
		"Employee",
		filters=filters,
		fields=["name", "employee_name", "designation", "status", "relieving_date", "date_of_joining"],
		order_by="name",
	)
	return [
		Member(row.name, row.employee_name, None, row.designation, BY_DESIGNATION)
		for row in employees
		if is_eligible(row, start, end)
	]


def apply_overrides(members: list[Member], rule: str, start: date, end: date) -> list[Member]:
	"""Exclude removes and Include adds people, using assignments whose dates overlap the period."""
	excluded = {row.employee for row in get_assignments(rule, start, end, "Exclude")}
	result = [member for member in members if member.employee not in excluded]
	present = {member.employee for member in result}
	for row in get_assignments(rule, start, end, "Include"):
		if row.employee not in present and row.employee not in excluded:
			result.append(get_hand_added_member(row.employee))
			present.add(row.employee)
	return result


def get_hand_added_member(employee: str) -> Member:
	values = frappe.db.get_value("Employee", employee, ["employee_name", "designation"], as_dict=True)
	return Member(employee, values.employee_name, None, values.designation, ADDED_BY_HAND)
