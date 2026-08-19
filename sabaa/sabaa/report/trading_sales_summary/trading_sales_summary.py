# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.query_builder.custom import GROUP_CONCAT
from frappe.utils import getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if filters.group_by not in ("Sales Order", "Sales Invoice"):
		frappe.throw(_("Please select Group By"))

	filters.from_date = getdate(filters.from_date or nowdate())
	filters.to_date = getdate(filters.to_date or nowdate())
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	columns = get_columns(filters)

	if filters.group_by == "Sales Invoice":
		invoices = fetch_sales_invoices(filters)
		order_map = get_linked_orders_for_invoices([row.document for row in invoices])
		data = [
			build_row(row, sales_invoice_id=row.document, sales_order_id=order_map.get(row.document))
			for row in invoices
		]
		report_summary = get_invoice_summary(invoices, order_map)
	else:
		orders = fetch_sales_orders(filters)
		returns = fetch_sales_invoices(filters, returns_only=True)
		invoice_map = get_linked_invoices_for_orders([row.document for row in orders])
		data = [
			build_row(row, sales_order_id=row.document, sales_invoice_id=invoice_map.get(row.document))
			for row in orders
		]
		if filters.get("include_returns"):
			data += [
				build_row(row, sales_order_id=None, sales_invoice_id=row.document) for row in returns
			]
			data.sort(key=lambda r: (r["posting_date"], r["sales_invoice_id"] or r["sales_order_id"]))
		report_summary = get_order_summary(orders, returns, invoice_map)

	return columns, data, None, None, report_summary


def get_columns(filters):
	amount_label = _("Invoiced Amount") if filters.group_by == "Sales Invoice" else _("Order Amount")

	return [
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Sales Order ID"),
			"fieldname": "sales_order_id",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 150,
		},
		{
			"label": _("Sales Invoice ID"),
			"fieldname": "sales_invoice_id",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150,
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Customer Group"),
			"fieldname": "customer_group",
			"fieldtype": "Link",
			"options": "Customer Group",
			"width": 150,
		},
		{
			"label": amount_label,
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Is Return"),
			"fieldname": "is_return",
			"fieldtype": "Check",
			"width": 90,
		},
		{
			"label": _("Returned Amount"),
			"fieldname": "returned_amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Salesperson"),
			"fieldname": "salesperson",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Visit ID"),
			"fieldname": "visit_id",
			"fieldtype": "Link",
			"options": "Visit",
			"width": 130,
		},
		{
			"label": _("Zone / Area"),
			"fieldname": "zone_or_area",
			"fieldtype": "Data",
			"width": 120,
		},
	]


def build_row(row, sales_order_id, sales_invoice_id):
	is_return = bool(row.get("is_return"))
	return {
		"posting_date": row.posting_date,
		"sales_order_id": sales_order_id,
		"sales_invoice_id": sales_invoice_id,
		"customer_name": row.customer_name,
		"customer_group": row.customer_group,
		"amount": row.amount,
		"is_return": is_return,
		"returned_amount": abs(row.amount) if is_return else 0,
		"salesperson": row.salesperson,
		"visit_id": row.visit_id,
		"zone_or_area": None,
	}


def get_order_summary(orders, returns, invoice_map):
	invoiced_count = sum(1 for row in orders if invoice_map.get(row.document))
	not_invoiced_count = len(orders) - invoiced_count
	returns_count = len(returns)
	total_count = len(orders) + returns_count

	return [
		{"label": _("Total Sales"), "value": total_count, "datatype": "Int", "indicator": "blue"},
		{"label": _("Orders (Invoiced)"), "value": invoiced_count, "datatype": "Int", "indicator": "green"},
		{
			"label": _("Orders (Not Invoiced)"),
			"value": not_invoiced_count,
			"datatype": "Int",
			"indicator": "orange",
		},
		{"label": _("Returns"), "value": returns_count, "datatype": "Int", "indicator": "red"},
	]


def get_invoice_summary(invoices, order_map):
	non_return = [row for row in invoices if not row.is_return]
	linked_count = sum(1 for row in non_return if order_map.get(row.document))
	not_linked_count = len(non_return) - linked_count
	returns_count = len(invoices) - len(non_return)
	total_count = len(invoices)

	return [
		{"label": _("Total Sales"), "value": total_count, "datatype": "Int", "indicator": "blue"},
		{
			"label": _("Invoices (Linked to Order)"),
			"value": linked_count,
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"label": _("Invoices (Not Linked to Order)"),
			"value": not_linked_count,
			"datatype": "Int",
			"indicator": "orange",
		},
		{"label": _("Returns"), "value": returns_count, "datatype": "Int", "indicator": "red"},
	]


def get_linked_invoices_for_orders(order_names):
	if not order_names:
		return {}

	sii = qb.DocType("Sales Invoice Item")
	si = qb.DocType("Sales Invoice")

	rows = (
		qb.from_(sii)
		.join(si)
		.on(si.name == sii.parent)
		.select(sii.sales_order, GROUP_CONCAT(sii.parent).distinct().as_("invoices"))
		.where(si.docstatus == 1)
		.where(si.is_return == 0)
		.where(sii.sales_order.isin(order_names))
		.groupby(sii.sales_order)
		.run(as_dict=True)
	)
	return {row.sales_order: row.invoices for row in rows}


def get_linked_orders_for_invoices(invoice_names):
	if not invoice_names:
		return {}

	sii = qb.DocType("Sales Invoice Item")

	rows = (
		qb.from_(sii)
		.select(sii.parent, GROUP_CONCAT(sii.sales_order).distinct().as_("orders"))
		.where(sii.parent.isin(invoice_names))
		.where(sii.sales_order.isnotnull())
		.where(sii.sales_order != "")
		.groupby(sii.parent)
		.run(as_dict=True)
	)
	return {row.parent: row.orders for row in rows}


def fetch_sales_invoices(filters, returns_only=False):
	si = qb.DocType("Sales Invoice")
	sii = qb.DocType("Sales Invoice Item")
	customer = qb.DocType("Customer")
	team = qb.DocType("Sales Team")

	query = (
		qb.from_(si)
		.left_join(customer)
		.on(si.customer == customer.name)
		.left_join(team)
		.on(team.parent == si.name)
		.select(
			si.name.as_("document"),
			si.posting_date,
			si.grand_total.as_("amount"),
			si.is_return,
			si.custom_visit.as_("visit_id"),
			customer.customer_name,
			customer.customer_group,
			GROUP_CONCAT(team.sales_person).distinct().as_("salesperson"),
		)
		.where(si.docstatus == 1)
		.where(si.posting_date >= filters.from_date)
		.where(si.posting_date <= filters.to_date)
		.groupby(si.name)
	)

	if returns_only:
		query = query.where(si.is_return == 1)
	if filters.get("customer_group"):
		query = query.where(customer.customer_group == filters.customer_group)
	if filters.get("customer"):
		query = query.where(si.customer == filters.customer)
	if filters.get("sales_person"):
		query = query.where(team.sales_person == filters.sales_person)
	if filters.get("item_group") or filters.get("item"):
		query = query.join(sii).on(sii.parent == si.name)
		if filters.get("item_group"):
			query = query.where(sii.item_group == filters.item_group)
		if filters.get("item"):
			query = query.where(sii.item_code == filters.item)

	return query.run(as_dict=True)


def fetch_sales_orders(filters):
	so = qb.DocType("Sales Order")
	soi = qb.DocType("Sales Order Item")
	customer = qb.DocType("Customer")
	team = qb.DocType("Sales Team")

	query = (
		qb.from_(so)
		.left_join(customer)
		.on(so.customer == customer.name)
		.left_join(team)
		.on(team.parent == so.name)
		.select(
			so.name.as_("document"),
			so.transaction_date.as_("posting_date"),
			so.grand_total.as_("amount"),
			so.custom_visit.as_("visit_id"),
			customer.customer_name,
			customer.customer_group,
			GROUP_CONCAT(team.sales_person).distinct().as_("salesperson"),
		)
		.where(so.docstatus == 1)
		.where(so.transaction_date >= filters.from_date)
		.where(so.transaction_date <= filters.to_date)
		.groupby(so.name)
	)

	if filters.get("customer_group"):
		query = query.where(customer.customer_group == filters.customer_group)
	if filters.get("customer"):
		query = query.where(so.customer == filters.customer)
	if filters.get("sales_person"):
		query = query.where(team.sales_person == filters.sales_person)
	if filters.get("item_group") or filters.get("item"):
		query = query.join(soi).on(soi.parent == so.name)
		if filters.get("item_group"):
			query = query.where(soi.item_group == filters.item_group)
		if filters.get("item"):
			query = query.where(soi.item_code == filters.item)

	rows = query.run(as_dict=True)
	for row in rows:
		row["is_return"] = 0
	return rows
