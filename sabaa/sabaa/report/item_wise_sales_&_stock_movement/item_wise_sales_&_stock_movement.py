# Copyright (c) 2025, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from sabaa.utils import format_quantity_by_uoms

def execute(filters=None):
    if not filters:
        filters = {}

    item_code = filters.get("item_code")    
    uom_filter = filters.get("uom") or "Pcs"
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    
    uom_map = get_uom_conversion_map(item_code)    

    columns = [
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Data", "width": 200},
        {"label": _("Quantity"), "fieldname": "quantity", "fieldtype": "Data", "width": 300},
        {"label": _("Avg Rate (Per {0})").format(uom_filter), "fieldname": "rate", "fieldtype": "Currency", "width": 200},
        {"label": _("Selling Value"), "fieldname": "value", "fieldtype": "Currency", "width": 120},
    ]

    sales_items = frappe.db.sql("""
        SELECT
            sii.parent AS invoice,
            si.customer,
            sii.qty,
            sii.amount,
            sii.uom
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE sii.item_code = %s
          AND si.docstatus = 1
          AND si.posting_date BETWEEN %s AND %s
    """, (item_code, from_date, to_date), as_dict=True)

    
    customer_map = {}

    for row in sales_items:
        customer = row.customer

        qty_pcs = row.qty * uom_map.get(row.uom, 1)

        if customer not in customer_map:
            customer_map[customer] = {
                "total_pcs": 0,
                "total_value": 0.0 # quantity * Selling rate
            }

        customer_map[customer]["total_pcs"] += qty_pcs
        customer_map[customer]["total_value"] += row.amount

    data = []

    for customer, info in customer_map.items():
        total_pcs = int(info["total_pcs"])
        total_value = info["total_value"]

        qty_for_rate = total_pcs / uom_map[uom_filter]
        avg_rate = (total_value / qty_for_rate) if qty_for_rate else 0
        qty_str = format_quantity_by_uoms(total_pcs, uom_map)        

        data.append({
            "customer": customer,
            "quantity": qty_str,
            "rate": avg_rate,
            "value": total_value
        })

    return columns, data

@frappe.whitelist()
def get_uom_conversion_map(item_code):
    """
    Returns:
    {
        "Pcs": 1,
        "Box": 6,
        "Ctn": 24
    }
    """
    conversions = frappe.db.sql("""
        SELECT uom, conversion_factor
        FROM `tabUOM Conversion Detail`
        WHERE parent = %s
    """, item_code, as_dict=True)

    stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")

    uom_map = {stock_uom: 1}

    for row in conversions:
        uom_map[row.uom] = row.conversion_factor

    return uom_map