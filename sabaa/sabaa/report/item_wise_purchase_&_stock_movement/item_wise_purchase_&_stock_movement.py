# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from sabaa.utils import format_quantity_by_uoms, get_uom_conversion_map

def execute(filters=None):
    if not filters:
        filters = {}

    item_code = filters.get("item_code")
    uom_filter = filters.get("uom") or "Pcs"
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    uom_map = get_uom_conversion_map(item_code)

    columns = [
        {"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Data", "width": 200},
        {"label": _("Quantity"), "fieldname": "quantity", "fieldtype": "Data", "width": 300},
        {"label": _("Avg. Rate (Per {0})").format(uom_filter), "fieldname": "rate", "fieldtype": "Currency", "width": 200},
        {"label": _("Full Amount"), "fieldname": "value", "fieldtype": "Currency", "width": 150},
    ]

    purchase_items = frappe.db.sql("""
        SELECT
            pii.parent AS invoice,
            pi.supplier AS supplier_id,
            pi.supplier_name AS supplier,
            pii.qty,
            pii.amount,
            pii.uom
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
        WHERE pii.item_code = %s
          AND pi.docstatus = 1
          AND pi.posting_date BETWEEN %s AND %s
    """, (item_code, from_date, to_date), as_dict=True)

    supplier_map = {}

    total_pcs_all = 0
    total_value_all = 0.0

    for row in purchase_items:
        supplier = row.supplier

        qty_pcs = row.qty * uom_map.get(row.uom, 1)

        if supplier not in supplier_map:
            supplier_map[supplier] = {
                "total_pcs": 0,
                "total_value": 0.0,
                "supplier_id": row.supplier_id
            }

        supplier_map[supplier]["total_pcs"] += qty_pcs
        supplier_map[supplier]["total_value"] += row.amount

        total_pcs_all += qty_pcs
        total_value_all += row.amount

    data = []

    for supplier, info in supplier_map.items():
        total_pcs = int(info["total_pcs"])
        total_value = info["total_value"]
        supplier_id = info["supplier_id"]

        qty_for_rate = total_pcs / uom_map[uom_filter]
        avg_rate = (total_value / qty_for_rate) if qty_for_rate else 0

        qty_str = format_quantity_by_uoms(total_pcs, uom_map)

        data.append({
            "supplier_id": supplier_id,
            "supplier": supplier,
            "quantity": qty_str,
            "rate": avg_rate,
            "value": total_value
        })

    # Totals Row
    total_qty_str = format_quantity_by_uoms(int(total_pcs_all), uom_map)
    avg_rate_total = (
        total_value_all / (total_pcs_all / uom_map[uom_filter])
        if total_pcs_all else 0
    )

    data.append({
        "supplier": "Total",
        "quantity": total_qty_str,
        "rate": avg_rate_total,
        "value": total_value_all
    })

    return columns, data
