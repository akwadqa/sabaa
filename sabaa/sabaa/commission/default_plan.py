"""Create the default plan from the rule templates; running it again returns the existing plan."""

import frappe

from sabaa.sabaa.commission.templates import RULE_TEMPLATES, apply_template

DEFAULT_PLAN_NAME = "Commission Map Jan–Jun 2026"
EXCLUDED_GROUP = "Direct Sales"


def create_default_plan(company: str, valid_from: str = "2026-01-01", valid_to: str = "2026-06-30") -> str:
	if frappe.db.exists("Commission Plan", DEFAULT_PLAN_NAME):
		return DEFAULT_PLAN_NAME

	plan = frappe.get_doc(
		{"doctype": "Commission Plan", "plan_name": DEFAULT_PLAN_NAME, "company": company,
		 "valid_from": valid_from, "valid_to": valid_to, "status": "Draft"}
	)
	if frappe.db.exists("Customer Group", EXCLUDED_GROUP):
		plan.append("excluded_customer_groups", {"customer_group": EXCLUDED_GROUP})
	plan.insert()

	names = {}
	for template_name in RULE_TEMPLATES:
		rule = frappe.new_doc("Commission Rule")
		rule.plan, rule.rule_name = plan.name, template_name
		apply_template(rule, template_name)
		names[template_name] = rule.insert().name

	for template_name, values in RULE_TEMPLATES.items():
		if values.get("paired_template"):
			frappe.db.set_value("Commission Rule", names[template_name], "paired_rule", names[values["paired_template"]])
	return plan.name
