"""Calculate a plan's commission lines for one payout month from its configured rules."""

from datetime import date

import frappe
from frappe import _
from frappe.utils import flt, getdate

from sabaa.sabaa.commission import basis as basis_module
from sabaa.sabaa.commission.basis import (
	DELIVERY_FEES,
	PAIRED_BASIS,
	BasisReader,
	build_month_values,
	format_month,
	get_period_range,
)
from sabaa.sabaa.commission.constants import LineStatus
from sabaa.sabaa.commission.distribution import split_pool
from sabaa.sabaa.commission.lines import CommissionLine
from sabaa.sabaa.commission.periods import PeriodMode, get_basis_months, month_end, month_start
from sabaa.sabaa.commission.recipients import (
	Member,
	apply_overrides,
	get_designation_members,
	get_group_supervisors,
	get_hand_added_member,
	get_tree_members,
)
from sabaa.sabaa.commission.setup_check import SetupProblem
from sabaa.sabaa.commission.tiers import calculate_tier, flat_rate, scale_tiers
from sabaa.sabaa.doctype.commission_assignment.commission_assignment import get_assignments

POOL = "Pool"
SUPERVISOR = "Supervisor of Sales Person Group"
TIERED, FLAT_RATE = "Tiered", "Flat Rate"
BY_ASSIGNMENT = "By Assignment %"


class CommissionEngine:
	def __init__(self, plan: str, month: date | str, reader: BasisReader | None = None):
		self.month = month_start(getdate(month))
		self.plan = frappe.get_doc("Commission Plan", plan)
		self.plan.excluded_groups = [row.customer_group for row in self.plan.excluded_customer_groups]
		self.settings = frappe.get_single("Commission Settings")
		self.erpnext_start = month_start(getdate(self.settings.erpnext_start_date))
		names = frappe.get_all("Commission Rule", filters={"plan": plan}, order_by="creation", pluck="name")
		self.rules = [frappe.get_doc("Commission Rule", name) for name in names]
		excluded_items = sorted({rate.item for rule in self.rules for rate in rule.unit_rates})
		self.reader = reader or BasisReader(self.plan, self.settings, excluded_items)
		self.problems: list[SetupProblem] = []

	def calculate(self) -> list[CommissionLine]:
		return [line for rule in self.rules for line in self.calculate_rule(rule.name)]

	def calculate_rule(self, rule_name: str) -> list[CommissionLine]:
		rule = next(rule for rule in self.rules if rule.name == rule_name)
		if rule.is_waiting_for_business:
			return [self.get_waiting_line(rule)]

		months = get_basis_months(PeriodMode(rule.period_mode), self.month)
		if months is None:
			return []
		if rule.basis == DELIVERY_FEES:
			return self.get_delivery_lines(rule)
		if rule.recipient_source == POOL:
			return self.get_pool_lines(rule, months)
		if rule.recipient_source == SUPERVISOR:
			return self.get_supervisor_lines(rule, months)
		if rule.basis == PAIRED_BASIS:
			return self.get_assistant_lines(rule, months)
		return self.get_attributed_lines(rule, months)

	# Each recipient type

	def get_waiting_line(self, rule) -> CommissionLine:
		note = rule.status_note or ""
		self.add_problem(rule, _("{0}: waiting for business input. {1}").format(rule.rule_name, note).strip(), rule)
		return self.new_line(rule, status=LineStatus.WAITING, notes=[note] if note else [])

	def get_attributed_lines(self, rule, months: list[date]) -> list[CommissionLine]:
		values, manual_months = self.get_values(rule, months, is_pooled=False)
		members = self.get_team_members(rule)
		keys = set(values) | {member.sales_person for member in members.values()}
		employees = get_sales_person_employees([key for key in keys if key])

		lines = []
		for key in sorted(keys, key=lambda key: key or ""):
			line = self.new_line(rule, sales_person=key)
			self.assign_attributed(line, rule, key, members, employees)
			self.set_basis(line, rule, values.get(key, {}), months, manual_months, key)
			self.set_tier(line, rule, rule.get_tiers())
			lines.append(line)
		return lines

	def get_supervisor_lines(self, rule, months: list[date]) -> list[CommissionLine]:
		values, manual_months = self.get_values(rule, months, is_pooled=False)
		supervisors = get_group_supervisors(rule.team_group) if rule.team_group else {}
		if not supervisors:
			self.add_problem(rule, _("Group {0} has no supervisor.").format(rule.team_group), {"doctype": "Sales Person", "name": rule.team_group})

		lines = []
		for group, supervisor in supervisors.items():
			team = [m for m in self.get_members_of(group, rule) if m.employee]
			team_values = sum_member_values(values, team)
			line = self.new_line(rule, employee=supervisor, notes=[_("Team {0}: {1} members").format(group, len(team))])
			self.set_basis(line, rule, team_values, months, manual_months, group)
			self.set_tier(line, rule, self.get_scaled_tiers(rule, len(team)))
			lines.append(line)
		return lines

	def get_assistant_lines(self, rule, months: list[date]) -> list[CommissionLine]:
		if not rule.paired_rule:
			self.add_problem(rule, _("{0}: choose the salesman rule it follows.").format(rule.rule_name), rule)
			return []
		paired = frappe.get_doc("Commission Rule", rule.paired_rule)
		values, manual_months = self.get_values(paired, months, is_pooled=False)

		lines = []
		for assignment in get_assignments(rule.name, months[0], month_end(self.month), "Assistant Of"):
			salesman = assignment.target_sales_person
			line = self.new_line(rule, employee=assignment.employee, sales_person=salesman)
			self.set_basis(line, rule, values.get(salesman, {}), months, manual_months, salesman)
			self.set_tier(line, rule, rule.get_tiers())
			lines.append(line)
		return lines

	def get_pool_lines(self, rule, months: list[date]) -> list[CommissionLine]:
		values, manual_months = self.get_values(rule, months, is_pooled=True)
		members_by_share, percents = self.get_share_members(rule)
		headcount = len(members_by_share.get(rule.headcount_share) or []) if rule.headcount_share else 0

		pool = self.new_line(rule)
		self.set_basis(pool, rule, values.get(None, {}), months, manual_months, None)
		self.set_tier(pool, rule, self.get_scaled_tiers(rule, headcount))
		if pool.status == LineStatus.MISSING_DATA:
			return [pool]

		lines = []
		for allocation in split_pool(pool.amount, rule.shares, members_by_share, percents):
			line = self.new_line(rule, **{key: getattr(pool, key) for key in BASIS_FIELDS})
			line.share_name, line.share_percent, line.amount = allocation.share_name, allocation.share_percent, allocation.amount
			line.status, line.notes = allocation.status, [allocation.note] if allocation.note else []
			if allocation.member:
				self.set_member(line, allocation.member)
			if allocation.note:
				self.add_problem(rule, _("{0}: shares total {1}%. They must total 100%.").format(rule.rule_name, allocation.note.split()[-1].rstrip("%")), {"action": "people", "rule": rule.name})
			lines.append(line)
		return lines

	def get_delivery_lines(self, rule) -> list[CommissionLine]:
		lines = []
		for row in self.reader.get_delivery_rows(rule, self.month, month_end(self.month)):
			bonus_orders = max(0, row.free_order_count - (rule.bonus_after_count or 0))
			amount = flat_rate(row.fee_amount, rule.flat_rate_percent or 0) + bonus_orders * flt(rule.bonus_per_unit)
			line = self.new_line(rule, employee=row.employee, basis_amount=row.fee_amount, fixed_part=flt(amount, 2))
			line.amount = flt(amount * (rule.payout_multiplier or 1), 2)
			line.month_values = {format_month(self.month): row.fee_amount}
			line.notes = [_("{0} free orders").format(row.free_order_count)]
			if not row.driver:
				line.status = LineStatus.NOT_ASSIGNED
				line.notes.append(_("These delivery invoices have no driver."))
				self.add_problem(rule, _("{0}: some delivery invoices have no driver.").format(rule.rule_name), rule)
			elif not row.employee:
				self.flag_no_employee(line, rule, _("Driver {0} has no employee.").format(row.driver), {"doctype": "Driver", "name": row.driver})
			lines.append(line)
		return lines

	# Shared steps

	def get_values(self, rule, months: list[date], is_pooled: bool):
		rows = self.reader.get_basis_rows(rule, *get_period_range(months))
		return build_month_values(rows, months, self.erpnext_start, rule.paired_rule or rule.name, is_pooled)

	def set_basis(self, line, rule, values: dict, months, manual_months, label) -> None:
		month_values = {month: values.get(month, None if month in manual_months else 0) for month in months}
		line.month_values = {format_month(month): value for month, value in month_values.items()}
		missing = [month for month, value in month_values.items() if value is None]
		if missing:
			line.notes.append(basis_module.missing_month_note(missing))
			if line.status == LineStatus.NOT_ASSIGNED:
				return  # sales outside the team: show them, but ask for no figures
			line.status = LineStatus.MISSING_DATA
			for month in missing:
				message = _("{0}: {1} figure missing for {2}.").format(rule.rule_name, format_month(month), label or _("the company"))
				self.add_problem(rule, message, {"action": "manual_figures", "rule": rule.name})
			return
		line.basis_amount = flt(sum(month_values.values()) / len(months), 2)

	def set_tier(self, line, rule, tiers) -> None:
		if line.basis_amount is None:
			return
		multiplier = rule.payout_multiplier or 1
		if rule.tier_method == TIERED:
			result = calculate_tier(line.basis_amount, tiers)
			line.target, line.next_target, line.gap_to_next = result.threshold, result.next_threshold, result.gap_to_next
			line.tier_label = _("{0} of {1}").format(result.tier_number, result.tier_count) if result.tier_number else _("Below tier 1")
			line.fixed_part, line.excess_part = result.fixed_part, result.excess_part
			amount = result.amount
		elif rule.tier_method == FLAT_RATE:
			amount = line.fixed_part = flat_rate(line.basis_amount, rule.flat_rate_percent or 0)
		else:
			amount = line.fixed_part = line.basis_amount
		line.amount = flt(amount * multiplier, 2)

	def get_scaled_tiers(self, rule, headcount: int):
		return scale_tiers(rule.get_tiers(), headcount, rule.headcount_base or 0, bool(rule.scale_amounts))

	def get_team_members(self, rule) -> dict[str, Member]:
		if not rule.team_group:
			return {}
		return {member.sales_person: member for member in self.get_members_of(rule.team_group, rule) if member.sales_person}

	def get_members_of(self, group: str, rule) -> list[Member]:
		start, end = self.get_period(rule)
		designations = [row.designation for row in rule.member_designations]
		return apply_overrides(get_tree_members(group, designations, start, end), rule.name, start, end)

	def get_share_members(self, rule) -> tuple[dict[str, list[Member]], dict[str, float]]:
		start, end = self.get_period(rule)
		percent_rows = get_assignments(rule.name, start, end, "Pool Share %")
		share_rows = get_assignments(rule.name, start, end, "Share Member")
		members_by_share = {}
		for share in rule.shares:
			if share.split == BY_ASSIGNMENT:
				members = [get_hand_added_member(row.employee) for row in percent_rows]
			elif share.designation:
				members = get_designation_members(share.designation, share.department, start, end)
			else:
				members = [get_hand_added_member(row.employee) for row in share_rows if row.share_name == share.share_name]
			members_by_share[share.share_name] = apply_overrides(members, rule.name, start, end)
		return members_by_share, {row.employee: flt(row.percent) for row in percent_rows}

	def get_period(self, rule) -> tuple[date, date]:
		return self.month, month_end(self.month)

	def assign_attributed(self, line, rule, key, members: dict[str, Member], employees: dict[str, frappe._dict]) -> None:
		if not key:
			line.status, line.notes = LineStatus.NOT_ASSIGNED, line.notes + [_("No sales person on these sales.")]
			return
		if members and key not in members:
			line.status = LineStatus.NOT_ASSIGNED
			line.notes.append(_("{0} is not an eligible member of {1}.").format(key, rule.team_group))
			return
		member = members.get(key)
		employee = member.employee if member else (employees.get(key) or {}).get("employee")
		if not employee:
			self.flag_no_employee(line, rule, _("Sales Person {0} has no employee.").format(key), {"doctype": "Sales Person", "name": key})
			return
		self.set_member(line, member or Member(employee, employees[key].employee_name, key, None, ""))

	def flag_no_employee(self, line, rule, message: str, fix: dict) -> None:
		if line.status == LineStatus.READY:
			line.status = LineStatus.NEEDS_SETUP
		line.notes.append(message)
		self.add_problem(rule, message, fix)

	def set_member(self, line, member: Member) -> None:
		line.employee = member.employee
		line.employee_name = member.employee_name
		line.sales_person = line.sales_person or member.sales_person

	def new_line(self, rule, **values) -> CommissionLine:
		line = CommissionLine(rule=rule.name, category=rule.category, role_label=rule.role_label or rule.rule_name, basis_label=rule.basis, **values)
		if line.employee and not line.employee_name:
			line.employee_name = frappe.db.get_value("Employee", line.employee, "employee_name")
		return line

	def add_problem(self, rule, message: str, fix) -> None:
		if not isinstance(fix, dict):
			fix = {"doctype": "Commission Rule", "name": fix.name}
		self.problems.append(SetupProblem(rule.name if rule else None, message, fix))


BASIS_FIELDS = ("month_values", "basis_amount", "target", "tier_label", "next_target", "gap_to_next", "fixed_part", "excess_part")


def sum_member_values(values: dict, members: list[Member]) -> dict[date, float | None]:
	"""Month totals over the members; a month missing for any member stays missing."""
	totals: dict[date, float | None] = {}
	for member in members:
		for month, amount in values.get(member.sales_person, {}).items():
			totals[month] = (totals.get(month) or 0) + amount
	return totals


def get_sales_person_employees(sales_persons: list[str]) -> dict[str, frappe._dict]:
	if not sales_persons:
		return {}
	rows = frappe.get_all(
		"Sales Person",
		filters={"name": ("in", sales_persons)},
		fields=["name", "employee", "employee.employee_name as employee_name"],
	)
	return {row.name: row for row in rows}
