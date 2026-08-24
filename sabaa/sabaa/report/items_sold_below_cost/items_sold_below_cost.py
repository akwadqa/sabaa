# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def execute(filters={}):
	columns = get_columns()
	data = get_data(filters)

	return columns, data

def get_columns():
	return [
		{
			"label": _("Sales Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice"
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date"
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"label": _("Item"),
			"fieldname": "item",
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"label": _("Quantity"),
			"fieldname": "qty",
			"fieldtype": "Float",
		},
		{
			"label": _("UOM"),
			"fieldname": "uom",
			"fieldtype": "Data",
		},
		{
			"label": _("Selling Rate"),
			"fieldname": "stock_uom_rate",
			"fieldtype": "Currency",
			"width": 165
		},
		{
			"label": _("Item Cost"),
			"fieldname": "incoming_rate",
			"fieldtype": "Currency",
			"width": 165
		},
		{
			"label": _("Loss"),
			"fieldname": "loss",
			"fieldtype": "Currency",
			"width": 165
		}
	]

def get_data(filters):
	si = frappe.qb.DocType("Sales Invoice")
	sii = frappe.qb.DocType("Sales Invoice Item")
	
	query = (
		frappe.qb.from_(si)
		.join(sii)
		.on(si.name == sii.parent)
		.select(
			si.name.as_("sales_invoice"),
			si.posting_date,
			si.customer_name.as_("customer"),
			sii.item_name.as_("item"),
			sii.stock_uom_rate,
			sii.incoming_rate,
			sii.qty,
			sii.uom
		)
		.where(si.docstatus == 1)
		.where(sii.parenttype == "Sales Invoice")
		.where(si.is_return == False)
		.where(sii.stock_uom_rate < sii.incoming_rate)
		.where(sii.is_free_item == False)
		.where(sii.stock_uom_rate != 0.00)
	)

	if filters.get("customer"):
		customers = filters.get("customer")
		if isinstance(customers, str):
			customers = [customers]
		
		query = query.where(si.customer.isin(customers))

	if filters.get("customer_group"):
		query = query.where(sii.item_group == filters.get("customer_group"))

	if filters.get("item_code"):
		item_code = filters.get("item_code")
		if isinstance(item_code, str):
			items = [item_code]
		
		query = query.where(si.item_code.isin(item_code))
	
	if filters.get("item_group"):
		query = query.where(sii.item_group == filters.get("item_group"))

	if filters.get("sales_invoice"):
		query = query.where(si.name == filters.get("sales_invoice"))

	if filters.get("from_date"):
		query = query.where(si.posting_date >= getdate(filters.get("from_date")))
	
	if filters.get("to_date"):
		query = query.where(si.posting_date <= getdate(filters.get("to_date")))
	
	if filters.get("company"):
		query = query.where(si.company == filters.get("company"))
	
	rows = query.run(as_dict=True)

	for row in rows:
		row["loss"] = row["incoming_rate"] - row["stock_uom_rate"]
	
	return rows

