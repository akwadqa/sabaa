"""Rule templates: the approved Jan–Jun 2026 commission map as editable starting points.

Names of customer groups, sales person groups, designations and items are the site's own (design §3).
Open business questions are cited by code (design §7) in each rule's note.
"""

import frappe

CASH, HYPER, ONLINE = "Cash Customers", "Hypermarket customers", "Online Sales"
CASH_TEAM, HYPER_TEAM = "Cash Market Salesman Sales", "Hypermarket Sales Executive Sales"
QUARTERLY, MONTHLY = "Quarterly Average", "Monthly"
SALES_DEPARTMENT = "Sales - STG"
SALESPERSON_THRESHOLDS = (70000, 84000, 105000, 131250, 157500)


def tiers(*rows: tuple) -> list[dict]:
	return [{"threshold": t, "fixed_amount": f, "excess_percent": e} for t, f, e in rows]


def sources(*rows: tuple[str, str]) -> list[dict]:
	return [{"customer_group": group, "measure": measure} for group, measure in rows]


def share(name: str, percent: float, designation: str | None = None, split: str = "Equal", department=None) -> dict:
	return {"share_name": name, "percent": percent, "designation": designation, "split": split, "department": department}


COMPANY_SALES = sources((CASH, "Collected"), (HYPER, "Invoiced"))

RULE_TEMPLATES: dict[str, dict] = {
	"Traditional Trade – Salesperson": {
		"category": "Traditional Trade", "role_label": "Salesperson", "basis": "Collected Sales",
		"basis_sources": sources((CASH, "Collected")), "period_mode": QUARTERLY,
		"tiers": tiers((70000, 200, 0), (84000, 367, 0), (105000, 1050, 0), (131250, 2362.5, 0), (157500, 3937.5, 3.5)),
		"team_group": CASH_TEAM, "member_designations": ["Salesman"],
		"status_note": "Quarterly or rolling average and payout multiplier to confirm (G4).",
	},
	"Traditional Trade – Cashier Assistant": {
		"category": "Traditional Trade", "role_label": "Cashier Assistant", "basis": "Paired Basis",
		"paired_template": "Traditional Trade – Salesperson", "period_mode": QUARTERLY,
		"tiers": tiers(*zip(SALESPERSON_THRESHOLDS, (75, 125, 200, 300, 400), (0, 0, 0, 0, 0.45))),
		"is_waiting_for_business": 1, "status_note": "Name the cashier assistants and their salesmen (S2).",
	},
	"Traditional Trade – Supervisor": {
		"category": "Traditional Trade", "role_label": "Supervisor", "basis": "Collected Sales",
		"basis_sources": sources((CASH, "Collected")), "period_mode": QUARTERLY,
		"tiers": tiers((672000, 1344, 0), (840000, 2646, 0), (1050000, 4966.5, 0), (1260000, 7938, 1)),
		"recipient_source": "Supervisor of Sales Person Group", "team_group": CASH_TEAM,
		"member_designations": ["Salesman"], "headcount_base": 8, "paired_template": "Traditional Trade – Salesperson",
		"status_note": "Salesmen of each supervisor (S1); amounts with fewer than 8 salesmen (S3).",
	},
	"Traditional Trade – Tea Milk": {
		"category": "Traditional Trade", "role_label": "Per Carton", "basis": "Unit Count",
		"basis_sources": sources((CASH, "Invoiced")), "period_mode": MONTHLY, "tier_method": "Unit Rate",
		"unit_rates": [{"item": "MR-MILK-00014", "uom": "Ctn", "amount_per_unit": 1}],
		"status_note": "Returns deduct cartons by default (U1).",
	},
	"Modern Trade – Salesperson Pool": {
		"category": "Modern Trade", "role_label": "Salesperson Pool", "basis": "Net Invoiced Sales",
		"basis_sources": sources((HYPER, "Invoiced")), "period_mode": QUARTERLY, "recipient_source": "Pool",
		"tiers": tiers((600000, 1800, 0), (700000, 1800, 1.25), (900000, 2500, 1.75), (1100000, 3500, 2)),
		"shares": [share("Salespersons", 100, split="By Assignment %")], "is_waiting_for_business": 1,
		"status_note": "Enter the 12 salespersons and their shares (M2); tier reading to confirm (M1).",
	},
	"Modern Trade – Supervisor": {
		"category": "Modern Trade", "role_label": "Supervisor", "basis": "Net Invoiced Sales",
		"basis_sources": sources((HYPER, "Invoiced")), "period_mode": QUARTERLY,
		"tiers": tiers((700000, 1000, 0), (900000, 2000, 0), (1100000, 2000, 1.5)),
		"recipient_source": "Supervisor of Sales Person Group", "team_group": HYPER_TEAM,
		"member_designations": ["Sales Executive", "Salesman"],
	},
	"Sales Management – Manager Pool": {
		"category": "Sales Management", "role_label": "Manager and Assistant", "basis": "Company Sales",
		"basis_sources": COMPANY_SALES, "period_mode": QUARTERLY, "recipient_source": "Pool",
		"tiers": tiers((1500000, 2000, 0), (1600000, 2000, 2)),
		"shares": [share("Manager", 60, "Sales Head"), share("Assistant", 40, "Sales Manager")],
		"status_note": "Is 2,000 earned from 1.5M or 1.6M (SM1)?",
	},
	"Sales Management – Coordinator": {
		"category": "Sales Management", "role_label": "Coordinator", "basis": "Company Sales",
		"basis_sources": COMPANY_SALES, "period_mode": QUARTERLY, "recipient_source": "Pool",
		"tiers": tiers((1500000, 350, 0)), "shares": [share("Coordinator", 100, "Sales Coordinator")],
	},
	"Smile24 – Online Salesperson": {
		"category": "Smile24", "role_label": "Online Salesperson", "basis": "Net Invoiced Sales",
		"basis_sources": sources((ONLINE, "Invoiced")), "period_mode": MONTHLY,
		"tiers": tiers((20000, 200, 0), (30000, 720, 0), (50000, 1700, 0), (70000, 2800, 5)),
		"status_note": "Invoiced or collected sales (O1); the two online salespersons (O2).",
	},
	"Smile24 – Drivers": {
		"category": "Smile24", "role_label": "Driver", "basis": "Delivery Fees",
		"basis_sources": sources((ONLINE, "Invoiced")), "attribute_by": "Invoice Driver", "period_mode": MONTHLY,
		"tier_method": "Flat Rate", "flat_rate_percent": 50, "bonus_after_count": 100, "bonus_per_unit": 5,
		"status_note": "Meaning of free delivery exceeding 100 (O3).",
	},
	"Logistics – Team": {
		"category": "Logistics", "role_label": "Logistics Team", "basis": "Company Sales",
		"basis_sources": sources((CASH, "Collected"), (HYPER, "Invoiced"), ("Van Sales", "Invoiced"), ("Horeca Customers", "Invoiced")),
		"period_mode": MONTHLY, "recipient_source": "Pool", "headcount_base": 8, "headcount_share": "Drivers",
		"shares": [share("Drivers", 60, "Delivery Driver", department=SALES_DEPARTMENT), share("Workers", 40, "labor", department=SALES_DEPARTMENT)],
		"is_waiting_for_business": 1, "status_note": "Logistics tiers not given (L1); which labor count as workers (L2).",
	},
	"Tenders": {
		"category": "Tenders", "role_label": "Tender Pool", "basis": "Tender Collections", "period_mode": MONTHLY,
		"tier_method": "Flat Rate", "flat_rate_percent": 1.5, "recipient_source": "Pool",
		"shares": [share("Sales Department", 40), share("Management", 60)], "is_waiting_for_business": 1,
		"status_note": "How a tender is identified (T1) and who receives each share (T2).",
	},
}

LINK_FIELDS = {"team_group": "Sales Person"}
CHILD_LINKS = {"basis_sources": ("customer_group", "Customer Group"), "unit_rates": ("item", "Item")}


def get_templates() -> list[dict]:
	return [{"name": name, "category": values["category"], "role_label": values["role_label"]} for name, values in RULE_TEMPLATES.items()]


def apply_template(rule_doc, template_name: str) -> None:
	"""Fill a rule from a template; links to records missing on this site are left empty."""
	values = dict(RULE_TEMPLATES[template_name])
	values.pop("paired_template", None)
	designations = values.pop("member_designations", [])
	for field, doctype in LINK_FIELDS.items():
		if values.get(field) and not frappe.db.exists(doctype, values[field]):
			values.pop(field)
	for table, (field, doctype) in CHILD_LINKS.items():
		values[table] = [row for row in values.get(table, []) if frappe.db.exists(doctype, row[field])]
	values["shares"] = [
		{**row, "designation": row["designation"] if frappe.db.exists("Designation", row["designation"] or "") else None,
		 "department": row["department"] if frappe.db.exists("Department", row["department"] or "") else None}
		for row in values.get("shares", [])
	]
	rule_doc.update(values)
	rule_doc.template = template_name
	rule_doc.set("member_designations", [{"designation": d} for d in designations if frappe.db.exists("Designation", d)])
