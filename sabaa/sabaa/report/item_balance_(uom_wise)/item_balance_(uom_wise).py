# Copyright (c) 2025, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from sabaa.utils import format_quantity_by_uoms


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        {
            "label": _("Item"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 230
        },       
        {
            "label": _("Item Group"),
            "fieldname": "item_group",
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 180
        },
        {
            "label": _("Warehouse"),
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 180
        },
        {
            "label": _("Stock UOM"),
            "fieldname": "stock_uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 100
        },
        {
            "label": _("Quantity"),
            "fieldname": "qty_display",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Valuation Rate (Per UOM)"),
            "fieldname": "rate",
            "fieldtype": "Currency",
            "width": 200
        },
        {
            "label": _("Stock Value"),
            "fieldname": "value",
            "fieldtype": "Currency",
            "width": 130
        }
    ]

def get_data(filters):
    conditions = []
    values = {}

    if filters.get("item_code"):
        conditions.append("b.item_code = %(item_code)s")
        values["item_code"] = filters["item_code"]

    if filters.get("item_group"):
        conditions.append("i.item_group = %(item_group)s")
        values["item_group"] = filters["item_group"]

    if filters.get("warehouse"):
        conditions.append("b.warehouse = %(warehouse)s")
        values["warehouse"] = filters["warehouse"]

    condition_sql = ""
    if conditions:
        condition_sql = " AND " + " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT
            b.item_code,
            i.item_group,
            i.stock_uom,
            b.warehouse,
            b.actual_qty,
            b.valuation_rate,
            GROUP_CONCAT(
                CONCAT(ucd.uom, ':', ucd.conversion_factor)
                ORDER BY ucd.conversion_factor DESC
                SEPARATOR ','
            ) AS uom_map
        FROM `tabBin` b
        INNER JOIN `tabItem` i
            ON i.name = b.item_code
        LEFT JOIN `tabUOM Conversion Detail` ucd
            ON ucd.parent = i.name
        WHERE b.actual_qty != 0
        {condition_sql}
        GROUP BY b.item_code, b.warehouse
        """,
        values,
        as_dict=True
    )

    frappe.log_error("Item Balance UOM Wise Report Data", rows)

    return build_rows(rows, filters)

def build_rows(rows, filters):
    data = []

    for row in rows:
        conversions = parse_uom_map(row)

        qty_display = format_quantity_by_uoms(
            row.actual_qty,
            conversions,
            row.stock_uom
        )

        rate = get_rate_per_uom(
            row.valuation_rate,
            conversions,
            filters.get("uom"),
            row.stock_uom
        )

        data.append({
            "item_code": row.item_code,
            "item_group": row.item_group,
            "warehouse": row.warehouse,
            "stock_uom": row.stock_uom,
            "qty_display": qty_display,
            "rate": rate, # valuation_rate * conversion factor of selected UOM or stock UOM
            "value": row.actual_qty * row.valuation_rate
        })

    return data

def parse_uom_map(row):
    """
    Converts:
        CTN:24,Box:6
    Into:
        [
            {'uom': 'CTN', 'conversion_factor': 24},
            {'uom': 'Box', 'conversion_factor': 6},
            {'uom': 'Pcs', 'conversion_factor': 1}
        ]
    """
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

def get_rate_per_uom(valuation_rate, conversions, selected_uom, stock_uom):
    if not selected_uom or selected_uom == stock_uom:
        return valuation_rate

    for row in conversions:
        if row["uom"] == selected_uom:
            return valuation_rate * row["conversion_factor"]

    return valuation_rate
