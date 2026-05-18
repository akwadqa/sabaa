# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.cash_flow.cash_flow import get_account_type_based_gl_data
from erpnext.accounts.report.gross_profit.gross_profit import GrossProfitGenerator


def execute(filters=None):
	if not filters:
		filters = frappe._dict()

	filters.currency = frappe.get_cached_value("Company", filters.company, "default_currency")

	columns = get_columns()
	data, total_indirect_expenses, total_selling_amount = get_data(filters)

	report_summary = [
		{
			"label": _("Total Selling Amount"),
			"value": total_selling_amount,
			"datatype": "Currency",
			"currency": filters.currency,
		},
		{
			"label": _("Total Indirect Expenses"),
			"value": total_indirect_expenses,
			"datatype": "Currency",
			"currency": filters.currency,
		},
	]

	return columns, data, None, None, report_summary


def get_columns():
	return [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 140,
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Qty Sold"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"label": _("Selling Amount"),
			"fieldname": "selling_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"label": _("Buying Amount"),
			"fieldname": "buying_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"label": _("Sales Proportion %"),
			"fieldname": "sales_proportion",
			"fieldtype": "Percent",
			"width": 140,
		},
		{
			"label": _("Allocated Indirect Expenses"),
			"fieldname": "allocated_indirect_expenses",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 200,
		},
		{
			"label": _("BEP (Value)"),
			"fieldname": "bep_value",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"label": _("BEP (Units)"),
			"fieldname": "bep_units",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]


def get_data(filters):
	gp_filters = frappe._dict(
		{
			"company": filters.company,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"group_by": "Item Code",
			"include_returned_invoices": 1,
		}
	)

	if filters.get("item_code"):
		gp_filters.item_code = filters.item_code

	if filters.get("item_group"):
		gp_filters.item_group = filters.item_group

	gp_data = GrossProfitGenerator(gp_filters)
	item_rows = gp_data.grouped_data

	if not item_rows:
		return [], 0, 0
	
	indirect_expense_filters = frappe._dict(
		{
			"company": filters.company,
			"start_date": filters.from_date,
			"end_date": filters.to_date,
			"account_type": "Indirect Expense",
			"include_default_book_entries": 0,
		}
	)
	total_indirect_expenses = abs(
		flt(get_account_type_based_gl_data(filters.company, indirect_expense_filters))
	)

	total_selling_amount = sum(flt(row.base_amount) for row in item_rows)

	data = []
	for row in item_rows:
		selling_amount = flt(row.base_amount)
		buying_amount = flt(row.buying_amount)
		gross_profit = flt(row.gross_profit)
		qty = flt(row.qty)

		sales_proportion = (selling_amount / total_selling_amount) if total_selling_amount else 0
		allocated = total_indirect_expenses * sales_proportion

		gp_pct = (gross_profit / abs(selling_amount)) if selling_amount else 0
		gp_per_unit = (gross_profit / qty) if qty else 0

		bep_value = (allocated / gp_pct) if gp_pct else 0
		bep_units = (allocated / gp_per_unit) if gp_per_unit else 0

		data.append(
			frappe._dict(
				{
					"item_code": row.item_code,
					"item_name": row.item_name,
					"qty": qty,
					"selling_amount": selling_amount,
					"buying_amount": buying_amount,
					"sales_proportion": flt(sales_proportion * 100, 2),
					"allocated_indirect_expenses": allocated,
					"bep_value": bep_value,
					"bep_units": bep_units,
					"currency": filters.currency,
				}
			)
		)

	return data, total_indirect_expenses, total_selling_amount
