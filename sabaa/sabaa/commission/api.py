"""Whitelisted entry points for the report, the Commission Run and the setup page."""

import frappe
from frappe import _
from frappe.utils import flt

from sabaa.sabaa.commission.constants import LineStatus
from sabaa.sabaa.commission.engine import CommissionEngine
from sabaa.sabaa.commission.setup_check import check_setup
from sabaa.sabaa.commission.tiers import calculate_tier, format_number, scale_tiers


def check_plan_permission(plan: str, permission: str = "read") -> None:
	frappe.has_permission("Commission Plan", permission, plan, throw=True)


@frappe.whitelist()
def get_commission_lines(plan: str, month: str) -> list[dict]:
	check_plan_permission(plan)
	return [line.as_dict() for line in CommissionEngine(plan, month).calculate()]


@frappe.whitelist()
def get_setup_status(plan: str, month: str) -> list[dict]:
	"""One row per rule: name, category, summary, status and its problems."""
	check_plan_permission(plan)
	problems = check_setup(plan, month)
	rules = frappe.get_all(
		"Commission Rule",
		filters={"plan": plan},
		fields=["name", "rule_name", "category", "summary", "is_waiting_for_business"],
		order_by="creation",
	)
	rows = []
	for rule in rules:
		rule_problems = [problem.as_dict() for problem in problems if problem.rule == rule.name]
		status = LineStatus.WAITING if rule.is_waiting_for_business else LineStatus.NEEDS_SETUP if rule_problems else LineStatus.READY
		rows.append({**rule, "status": str(status), "problems": rule_problems})
	general = [problem.as_dict() for problem in problems if not problem.rule]
	if general:
		rows.insert(0, {"name": None, "rule_name": _("Settings"), "category": None, "summary": "", "status": str(LineStatus.NEEDS_SETUP), "problems": general})
	return rows


@frappe.whitelist()
def preview_tier(rule: str, amount: float, headcount: int | None = None) -> dict:
	"""The tier result for an amount, through the same tier functions the engine uses."""
	doc = frappe.get_doc("Commission Rule", rule)
	check_plan_permission(doc.plan)
	tiers = doc.get_tiers()
	if headcount and doc.headcount_base:
		tiers = scale_tiers(tiers, int(headcount), doc.headcount_base, bool(doc.scale_amounts))
	result = calculate_tier(flt(amount), tiers)
	total = flt(result.amount * (doc.payout_multiplier or 1), 2)
	tier_text = _("Tier {0} of {1}").format(result.tier_number, result.tier_count) if result.tier_number else _("Below tier 1")
	text = f"{format_number(flt(amount))} → {tier_text} → {format_number(total)} QAR"
	if headcount and doc.headcount_base and tiers:
		text += " · " + _("Target for {0}: {1}").format(headcount, format_number(tiers[0].threshold))
	return {"amount": total, "tier_number": result.tier_number, "text": text}


@frappe.whitelist()
def copy_plan(plan: str, new_name: str, valid_from: str, valid_to: str | None = None) -> str:
	"""Copy a plan and its rules as a Draft for a new period."""
	check_plan_permission(plan, "write")
	source = frappe.get_doc("Commission Plan", plan)
	copy = frappe.copy_doc(source)
	copy.update({"plan_name": new_name, "valid_from": valid_from, "valid_to": valid_to, "status": "Draft"})
	copy.insert()
	for rule_name in frappe.get_all("Commission Rule", filters={"plan": plan}, pluck="name"):
		rule_copy = frappe.copy_doc(frappe.get_doc("Commission Rule", rule_name))
		rule_copy.plan = copy.name
		rule_copy.paired_rule = None
		rule_copy.insert()
	_relink_paired_rules(plan, copy.name)
	return copy.name


def _relink_paired_rules(source_plan: str, target_plan: str) -> None:
	for rule in frappe.get_all("Commission Rule", filters={"plan": source_plan, "paired_rule": ("is", "set")}, fields=["rule_name", "paired_rule"]):
		paired_name = frappe.db.get_value("Commission Rule", rule.paired_rule, "rule_name")
		target = frappe.db.get_value("Commission Rule", {"plan": target_plan, "rule_name": paired_name})
		frappe.db.set_value("Commission Rule", {"plan": target_plan, "rule_name": rule.rule_name}, "paired_rule", target)


@frappe.whitelist()
def get_people(rule: str, month: str) -> list[dict]:
	from sabaa.sabaa.commission import people

	check_plan_permission(frappe.db.get_value("Commission Rule", rule, "plan"))
	return people.get_people(rule, month)


@frappe.whitelist()
def save_people(rule: str, month: str, rows: list | str) -> None:
	from sabaa.sabaa.commission import people

	check_plan_permission(frappe.db.get_value("Commission Rule", rule, "plan"), "write")
	people.save_people(rule, month, frappe.parse_json(rows))


@frappe.whitelist()
def get_missing_figure_grid(plan: str) -> dict:
	from sabaa.sabaa.commission import figures_grid

	check_plan_permission(plan)
	return figures_grid.get_missing_figure_grid(plan)


@frappe.whitelist()
def save_missing_figures(plan: str, rows: list | str) -> None:
	from sabaa.sabaa.commission import figures_grid

	check_plan_permission(plan, "write")
	figures_grid.save_missing_figures(plan, frappe.parse_json(rows))


@frappe.whitelist()
def create_default_plan(company: str | None = None) -> str:
	from sabaa.sabaa.commission import default_plan

	frappe.has_permission("Commission Plan", "create", throw=True)
	company = company or frappe.db.get_single_value("Commission Settings", "company")
	return default_plan.create_default_plan(company)


@frappe.whitelist()
def get_templates() -> list[dict]:
	from sabaa.sabaa.commission import templates

	return templates.get_templates()


@frappe.whitelist()
def apply_rule_template(rule: str, template: str) -> None:
	"""Fill an existing rule from a template (the rule form's template picker)."""
	from sabaa.sabaa.commission.templates import apply_template

	doc = frappe.get_doc("Commission Rule", rule)
	check_plan_permission(doc.plan, "write")
	apply_template(doc, template)
	doc.save()


@frappe.whitelist()
def create_rule_from_template(plan: str, template: str, rule_name: str | None = None) -> str:
	"""Create a rule in `plan` filled from `template` (the plan form's New rule dialog)."""
	from sabaa.sabaa.commission.templates import apply_template

	check_plan_permission(plan, "write")
	rule = frappe.new_doc("Commission Rule")
	rule.plan, rule.rule_name = plan, rule_name or template
	apply_template(rule, template)
	return rule.insert().name
