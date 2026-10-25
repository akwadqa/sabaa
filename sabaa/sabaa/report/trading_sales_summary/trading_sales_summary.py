# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.query_builder.custom import GROUP_CONCAT
from frappe.query_builder.functions import Coalesce, NullIf
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
		invoices = attach_and_filter_area_info(fetch_sales_invoices(filters), filters)
		order_map = get_linked_orders_for_invoices([row.document for row in invoices])
		data = [
			build_row(row, sales_invoice_id=row.document, sales_order_id=order_map.get(row.document))
			for row in invoices
		]
		report_summary = get_invoice_summary(invoices, order_map)
	else:
		orders = attach_and_filter_area_info(fetch_sales_orders(filters), filters)
		returns = attach_and_filter_area_info(
			fetch_sales_invoices(filters, returns_only=True), filters
		)
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
			"label": _("Area"),
			"fieldname": "area",
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
		"area": row.get("area"),
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


def get_trip_for_visits(visit_ids):
	if not visit_ids:
		return {}
	rows = frappe.get_all("Visit", filters={"name": ["in", list(visit_ids)]}, fields=["name", "trip"])
	return {row.name: row.trip for row in rows}


def get_area_for_trips(trip_ids):
	trip_ids = [name for name in trip_ids if name]
	if not trip_ids:
		return {}
	rows = frappe.get_all("Trip", filters={"name": ["in", trip_ids]}, fields=["name", "custom_assigned_area"])
	return {row.name: row.custom_assigned_area for row in rows}


def get_area_for_sales_persons(sales_person_names):
	sales_person_names = [name for name in sales_person_names if name]
	if not sales_person_names:
		return {}
	rows = frappe.get_all(
		"Sales Person", filters={"name": ["in", sales_person_names]}, fields=["name", "custom_assigned_area"]
	)
	return {row.name: row.custom_assigned_area for row in rows}


def get_area_for_addresses(address_names):
	address_names = [name for name in address_names if name]
	if not address_names:
		return {}
	rows = frappe.get_all("Address", filters={"name": ["in", address_names]}, fields=["name", "custom_area"])
	return {row.name: row.custom_area for row in rows}


def get_details_for_areas(area_names):
	area_names = [name for name in area_names if name]
	if not area_names:
		return {}
	rows = frappe.get_all(
		"Area", filters={"name": ["in", area_names]}, fields=["name", "area_name", "zone"]
	)
	return {row.name: row for row in rows}


def attach_and_filter_area_info(rows, filters):
	visit_ids = {row.get("visit_id") for row in rows if row.get("visit_id")}
	trip_by_visit = get_trip_for_visits(visit_ids)
	area_by_trip = get_area_for_trips(trip_by_visit.values())

	sales_person_names = set()
	for row in rows:
		if row.get("salesperson"):
			sales_person_names.update(name for name in row["salesperson"].split(",") if name)
	area_by_sales_person = get_area_for_sales_persons(sales_person_names)
	area_by_address = get_area_for_addresses({row.get("customer_address") for row in rows})

	area_names = (
		set(area_by_trip.values()) | set(area_by_sales_person.values()) | set(area_by_address.values())
	)
	area_details = get_details_for_areas(area_names)

	area_filter = filters.get("area")
	zone_filter = filters.get("zone")

	filtered_rows = []
	for row in rows:
		trip_area = area_by_trip.get(trip_by_visit.get(row.get("visit_id")))
		sales_person_areas = [
			area_by_sales_person[name]
			for name in (row.get("salesperson") or "").split(",")
			if area_by_sales_person.get(name)
		]
		customer_area = area_by_address.get(row.get("customer_address"))
		candidate_areas = [
			area for area in [trip_area, *sales_person_areas, customer_area] if area
		]
		candidate_zones = {
			area_details[area].zone for area in candidate_areas if area_details.get(area)
		}

		if area_filter and area_filter not in candidate_areas:
			continue
		if zone_filter and zone_filter not in candidate_zones:
			continue

		resolved_area = candidate_areas[0] if candidate_areas else None
		row["area"] = area_details[resolved_area].area_name if area_details.get(resolved_area) else None
		filtered_rows.append(row)

	return filtered_rows


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
			Coalesce(NullIf(si.customer_address, ""), customer.customer_primary_address).as_(
				"customer_address"
			),
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
			Coalesce(NullIf(so.customer_address, ""), customer.customer_primary_address).as_(
				"customer_address"
			),
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
