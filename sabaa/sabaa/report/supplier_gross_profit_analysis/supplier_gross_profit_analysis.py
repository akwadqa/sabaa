# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.report.gross_profit.gross_profit import GrossProfitGenerator


def execute(filters=None):

    filters = frappe._dict(filters or {})

    validate_filters(filters)

    columns = get_columns()

    sales_cogs_data = get_sales_and_cogs(filters)

    purchase_data = get_purchase_data(filters)

    data = allocate_by_supplier(
        sales_cogs_data,
        purchase_data,
        filters
    )

    data = add_grand_total(data)

    return columns, data

def validate_filters(filters):

    if not filters.company:
        frappe.throw(_("Company is required"))

    if not filters.from_date:
        frappe.throw(_("From Date is required"))

    if not filters.to_date:
        frappe.throw(_("To Date is required"))
    
def get_columns():
    return [
        {
            "label": _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Sold Qty"),
            "fieldname": "sold_qty",
            "fieldtype": "Float",
            "width": 120,
        },
        {
            "label": _("Allocated Revenue"),
            "fieldname": "revenue",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "label": _("Allocated COGS"),
            "fieldname": "cogs",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "label": _("Allocated Gross Profit"),
            "fieldname": "gross_profit",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": _("Gross Profit %"),
            "fieldname": "gross_profit_percent",
            "fieldtype": "Percent",
            "width": 140,
        },
    ]

def get_sales_and_cogs(filters):
    filters.currency = frappe.get_cached_value("Company", filters.company, "default_currency")
    filters.group_by = "Invoice"

    gp = GrossProfitGenerator(filters)    

    rows = gp.si_list

    frappe.log_error("Gross Profit Data", str(rows))

    item_map = {}

    for r in rows:

        if not r.item_code:
            continue

        item = item_map.setdefault(r.item_code, {
            "item_name": r.item_name,
            "sold_qty": 0,
            "revenue": 0,
            "cogs": 0
        })

        item["sold_qty"] += r.qty
        item["revenue"] += r.base_net_amount
        item["cogs"] += r.buying_amount
    
    return item_map

def get_purchase_data(filters):
    values = filters

    pi_conditions = [
        "pi.docstatus = 1",
        "pi.update_stock = 1",
        "pi.company = %(company)s",
        "pi.posting_date <= %(to_date)s"
    ]

    pr_conditions = [
        "pr.docstatus = 1",
        "pr.company = %(company)s",
        "pr.posting_date <= %(to_date)s"
    ]

    if filters.item_code:
        pi_conditions.append("pii.item_code = %(item_code)s")
        pr_conditions.append("pri.item_code = %(item_code)s")

    if filters.item_group:
        pi_conditions.append("i.item_group = %(item_group)s")
        pr_conditions.append("i.item_group = %(item_group)s")

    if filters.warehouse:
        pi_conditions.append("pii.warehouse = %(warehouse)s")
        pr_conditions.append("pri.warehouse = %(warehouse)s")

    pi_conditions_str = " AND ".join(pi_conditions)
    pr_conditions_str = " AND ".join(pr_conditions)

    query = f"""
        SELECT
            item_code,
            supplier,
            SUM(buy_qty) AS buy_qty
        FROM (
            SELECT
                pii.item_code AS item_code,
                pi.supplier AS supplier,
                pii.stock_qty AS buy_qty
            FROM `tabPurchase Invoice` pi
            INNER JOIN `tabPurchase Invoice Item` pii
                ON pii.parent = pi.name
            INNER JOIN `tabItem` i
                ON i.name = pii.item_code
            WHERE {pi_conditions_str}

            UNION ALL

            SELECT
                pri.item_code AS item_code,
                pr.supplier AS supplier,
                pri.stock_qty AS buy_qty
            FROM `tabPurchase Receipt` pr
            INNER JOIN `tabPurchase Receipt Item` pri
                ON pri.parent = pr.name
            INNER JOIN `tabItem` i
                ON i.name = pri.item_code
            WHERE {pr_conditions_str}
        ) combined
        GROUP BY
            item_code,
            supplier
    """

    return frappe.db.sql(query, values, as_dict=True)

def allocate_by_supplier(sales_cogs_data, purchase_data, filters):

    purchase_map, totals = build_purchase_map(purchase_data)

    data = []

    for item_code, s in sales_cogs_data.items():

        suppliers = purchase_map.get(item_code)

        if not suppliers:
            continue

        total_buy_qty = totals[item_code]

        if not total_buy_qty:
            continue

        for sup in suppliers:

            if filters.get("supplier") and sup.supplier != filters.supplier:
                continue

            ratio = flt(sup.buy_qty) / flt(total_buy_qty)

            revenue = s["revenue"] * ratio
            cogs = s["cogs"] * ratio
            gp = revenue - cogs

            data.append({                
                "supplier": f"<a href='{frappe.utils.get_url_to_form("Supplier", sup.supplier)}' target='_blank'>{sup.supplier}</a>",
                "item_code": f"<a href='{frappe.utils.get_url_to_form("Item", item_code)}' target='_blank'>{item_code}</a>",
                "item_name": f"<a href='{frappe.utils.get_url_to_form("Item", item_code)}' target='_blank'>{s['item_name']}</a>",
                "sold_qty": s["sold_qty"] * ratio,
                "revenue": revenue,
                "cogs": cogs,
                "gross_profit": gp,
                "gross_profit_percent": (gp / revenue * 100) if revenue else 0
            })

    return data

def build_purchase_map(purchase_data):

    purchase_map = {}
    totals = {}

    for row in purchase_data:

        purchase_map.setdefault(row.item_code, []).append(row)

        totals[row.item_code] = totals.get(row.item_code, 0) + row.buy_qty

    return purchase_map, totals

def add_grand_total(data):

    total = {
        "supplier": "Grand Total",
        "revenue": 0,
        "cogs": 0,
        "gross_profit": 0,
        "sold_qty": 0,
        "gross_profit_percent": 0
    }

    for d in data:

        total["revenue"] += d["revenue"]
        total["cogs"] += d["cogs"]
        total["gross_profit"] += d["gross_profit"]
        total["sold_qty"] += d["sold_qty"]

    if total["revenue"]:
        total["gross_profit_percent"] = flt(
            (total["gross_profit"] / total["revenue"]) * 100, 2
        ) if total["revenue"] else 0

    data.append(total)

    return data

