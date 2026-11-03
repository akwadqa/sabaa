# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.report.stock_ledger.stock_ledger import execute as stock_ledger_execute

# Valuation fields of the native Stock Ledger. "Include UOM" adds "<fieldname>_<uom>" variants.
VALUE_FIELDNAMES = ("incoming_rate", "valuation_rate", "in_out_rate", "stock_value", "stock_value_difference")


def execute(filters=None):
	columns, data = stock_ledger_execute(filters)
	columns = [column for column in columns if not is_value_field(column["fieldname"])]
	# Strip the values from the rows too, so they never reach the browser.
	data = [{key: value for key, value in row.items() if not is_value_field(key)} for row in data]

	for column in columns:
		# The report runner rejects rows that link to a doctype the user cannot read
		# (e.g. Sales User on Serial and Batch Bundle), so show those links as plain text.
		if column.get("fieldtype") == "Link" and not frappe.has_permission(column["options"], "read"):
			column["fieldtype"] = "Data"
			column.pop("options")

	return columns, data


def is_value_field(fieldname: str) -> bool:
	return fieldname.startswith(VALUE_FIELDNAMES)
