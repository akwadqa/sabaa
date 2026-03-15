# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, get_url_to_form, escape_html
from frappe.query_builder import DocType
from frappe.query_builder.functions import Concat, Sum, CustomFunction
from sabaa.utils import format_quantity_by_uoms

def execute(filters=None):

	columns = get_columns(filters)

	data = data_query(filters)
	
	return columns, data

def get_columns(filters):
	return [
		{
			"label": _("Customer"),
			"fieldtype": "Data",
			"fieldname": "customer",
			"width": 315,
		},
		{
			"label": _("Item Code"),
			"fieldtype": "Data",
			"fieldname": "item_code",
			"options": "Item",
			"width": 300,
		},
		{
			"label": _("Item Name"), 
			"fieldtype": "Data", 
			"fieldname": "item_name", 
			"width": 350
		},
		{
			"label": _("Total Free Quantity"),
			"fieldtype": "Data",
			"fieldname": "total_free_qty",
			"width": 250,
		}
	]


def data_query(filters):
	sales_invoice = frappe.qb.DocType("Sales Invoice")
	invoice_item = frappe.qb.DocType("Sales Invoice Item")
	item = frappe.qb.DocType("Item")
	ucd = frappe.qb.DocType("UOM Conversion Detail")

	qty_query = (
		frappe.qb.from_(sales_invoice)
		.join(invoice_item)
		.on(sales_invoice.name == invoice_item.parent)
		.select(
			sales_invoice.customer.as_("customer"),
			sales_invoice.customer_name.as_("customer_name"),
			invoice_item.item_code.as_("item_code"),
			invoice_item.stock_uom.as_("stock_uom"),
			Sum(invoice_item.stock_qty).as_("qty")
		).where(sales_invoice.docstatus == 1)
		.where(invoice_item.parenttype == "Sales Invoice")
		.where( (invoice_item.is_free_item == 1) | (invoice_item.rate == 0) )
		.groupby(invoice_item.item_name)
	)

	if filters.get("customer"):
		qty_query = qty_query.where(sales_invoice.customer == filters["customer"])

	if filters.get("company"):
		qty_query = qty_query.where(sales_invoice.company == filters["company"])

	if filters.get("from_date"):
		qty_query = qty_query.where(sales_invoice.posting_date >= filters["from_date"])

	if filters.get("to_date"):
		qty_query = qty_query.where(sales_invoice.posting_date <= filters["to_date"])

	qty_sql = qty_query.get_sql()
	
	main_query = frappe.db.sql(
		f"""
		SELECT
			qty_query.customer AS customer,
			qty_query.customer_name AS customer_name,
			item.item_code AS item_code,
			item.item_name AS item_name,
			qty_query.stock_uom AS stock_uom,
			qty_query.qty AS qty,
			GROUP_CONCAT(
				CONCAT(ucd.uom, ':', ucd.conversion_factor)
                ORDER BY ucd.conversion_factor DESC
                SEPARATOR ','
            ) AS uom_map
		FROM 
			({qty_sql}) AS qty_query
			LEFT JOIN `tabItem` AS item
			ON qty_query.item_code = item.name
			LEFT JOIN `tabUOM Conversion Detail` AS ucd
			ON ucd.parent = item.name
		GROUP BY item.name
		""",
		as_dict=True
	)

	return build_rows(main_query, filters)

def build_rows(rows, filters):
	data = []

	for row in rows:
		conversions = parse_uom_map(row)

		total_free_qty = format_quantity_by_uoms(
            row.qty,
            conversions,
            row.uom
        )

		item_code, item_name = get_item_links(row.item_code, row.item_name)
		customer_name = get_customer_link(row.customer, row.customer_name)

		data.append({
			"customer": customer_name,
			"item_name": item_name,
			"item_code": item_code,
			"total_free_qty": total_free_qty
		})
	
	return data

def parse_uom_map(row):
    # CTN:24,Box:6 --> [{'uom': 'CTN', 'conversion_factor':24}...]

    conversions = []

    if row.uom_map:
        for part in row.uom_map.split(","):
            uom, factor = part.split(":")
            conversions.append({
                "uom": uom,
                "conversion_factor": float(factor)
            })

    return sorted(
        conversions,
        key=lambda x: x["conversion_factor"],
        reverse=True
    )

def get_item_links(item_code, item_name):
    return (
        f'<a href="{get_url_to_form("Item", item_code)}" '
        f'target="_blank" rel="noopener noreferrer">'
        f'{escape_html(item_code)}'
        f'</a>'
    ), (
        f'<a href="{get_url_to_form("Item", item_code)}" '
        f'target="_blank" rel="noopener noreferrer">'
        f'{escape_html(item_name)}'
        f'</a>'
    )

def get_customer_link(customer, customer_name):
    return (
        f'<a href="{get_url_to_form("Customer", customer)}" '
        f'target="_blank" rel="noopener noreferrer">'
        f'{escape_html(customer_name)}'
        f'</a>'
    )