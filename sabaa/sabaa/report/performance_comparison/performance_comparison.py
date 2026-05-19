# Copyright (c) 2026, Akwad and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import add_days, add_months, date_diff, flt, getdate

from erpnext.accounts.report.financial_statements import get_data, get_period_list
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import (
	get_net_profit_loss,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.accumulated_values = filters.get("accumulated_values", 0)
	filters.show_zero_values = filters.get("show_zero_values", 0)

	# Step 2 — Build the selected period list
	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		"Yearly",
		company=filters.company,
	)

	# Step 3 — Derive the comparison period dates
	from_date = period_list[0]["from_date"]
	to_date = period_list[-1]["to_date"]

	if filters.comparison_type == "Year-over-Year":
		comp_from = add_months(from_date, -12)
		comp_to = add_months(to_date, -12)

	elif filters.comparison_type == "Previous Period":
		duration = date_diff(to_date, from_date) + 1
		comp_to = add_days(from_date, -1)
		comp_from = add_days(comp_to, -(duration - 1))

	else:  # Custom
		comp_from = getdate(filters.comparison_start_date)
		comp_to = getdate(filters.comparison_end_date)

	# Step 4 — Build the comparison period list
	comparison_period_list = get_period_list(
		None,
		None,
		comp_from,
		comp_to,
		"Date Range",
		"Yearly",
		company=filters.company,
		ignore_fiscal_year=True,
	)

	# Step 5 — Fetch GL data for both periods
	income_current = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
	)

	income_comparison = get_data(
		filters.company,
		"Income",
		"Credit",
		comparison_period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
	)

	expense_current = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
	)

	expense_comparison = get_data(
		filters.company,
		"Expense",
		"Debit",
		comparison_period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
	)

	# Step 6 — Compute Net Profit/Loss for both periods
	net_profit_current = get_net_profit_loss(
		income_current, expense_current, period_list, filters.company, filters.presentation_currency
	)

	net_profit_comparison = get_net_profit_loss(
		income_comparison,
		expense_comparison,
		comparison_period_list,
		filters.company,
		filters.presentation_currency,
	)

	# Step 7 — Merge datasets and compute difference / % change
	cur_key = period_list[0]["key"]
	comp_key = comparison_period_list[0]["key"]

	comparison_lookup = {}
	for dataset in [income_comparison, expense_comparison]:
		if dataset:
			for row in dataset:
				if row.get("account"):
					comparison_lookup[row["account"]] = row

	all_current = []
	all_current.extend(income_current or [])
	all_current.extend(expense_current or [])

	data = []
	for row in all_current:
		if row.get("account"):
			row["account"] = row["account"].strip("'")
		if row.get("account_name"):
			row["account_name"] = row["account_name"].strip("'")

		current_val = flt(row.get(cur_key, 0))
		comp_row = comparison_lookup.get(row.get("account"), {})
		comparison_val = flt(comp_row.get(comp_key, 0))
		difference = current_val - comparison_val
		pct_change = flt((difference / abs(comparison_val)) * 100, 2) if comparison_val else None

		row["current_value"] = current_val
		row["comparison_value"] = comparison_val
		row["difference"] = difference
		row["pct_change"] = pct_change
		data.append(row)

	# Step 8 — Merge the Net Profit/Loss row separately
	if net_profit_current:
		net_profit_current["account"] = net_profit_current["account"].strip("'")
		net_profit_current["account_name"] = net_profit_current["account_name"].strip("'")

		cur_npl = flt(net_profit_current.get(cur_key, 0))
		comp_npl = flt(net_profit_comparison.get(comp_key, 0)) if net_profit_comparison else 0
		diff_npl = cur_npl - comp_npl
		pct_npl = flt((diff_npl / abs(comp_npl)) * 100, 2) if comp_npl else None

		net_profit_current["current_value"] = cur_npl
		net_profit_current["comparison_value"] = comp_npl
		net_profit_current["difference"] = diff_npl
		net_profit_current["pct_change"] = pct_npl
		data.append(net_profit_current)

	# Step 9 — Build columns and return
	currency = filters.presentation_currency or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)

	columns = [
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Data",
			"width": 300,
		},
		{
			"label": _("First Period") if (filters.comparison_type == "Custom" and filters.filter_based_on == "Date Range") else period_list[0]["label"],
			"fieldname": "current_value",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 160,
		},
		{
			"label": _("Second Period") if (filters.comparison_type == "Custom" and filters.filter_based_on == "Date Range") else comparison_period_list[0]["label"],
			"fieldname": "comparison_value",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 160,
		},
		{
			"label": _("Difference"),
			"fieldname": "difference",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 160,
		},
		{
			"label": _("% Change"),
			"fieldname": "pct_change",
			"fieldtype": "Percent",
			"width": 100,
		},
	]

	return columns, data
