import frappe
from frappe import _
from frappe.utils import flt, getdate, today


MOCI_PARENT_GROUP = "MOCI Category"


def execute(filters=None):
    filters = filters or {}

    company = filters.get("company")
    as_on_date = getdate(filters.get("date") or today())

    if not company:
        frappe.throw(_("Company is required"))

    columns = get_columns()
    data = get_data(company, as_on_date)

    return columns, data


def get_columns():
    return [
        {
            "fieldname": "moci_category",
            "label": _("MoCI Category"),
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 280,
        },
        {
            "fieldname": "total_ton_qty",
            "label": _("Current Qty (Ton)"),
            "fieldtype": "Float",
            "width": 180,
        },
    ]


def get_data(company, as_on_date):
    # 1) Get all MoCI categories (Item Groups where parent is "MOCI Category")
    categories = frappe.get_all(
        "Item Group",
        filters={"parent_item_group": MOCI_PARENT_GROUP},
        pluck="name",
        order_by="name",
    )

    totals_by_category = {c: 0 for c in categories}
    uncategorized_total = 0

    # 2) Fetch balance qty per item_code as-of date, and bring item fields
    rows = frappe.db.sql(
        """
        SELECT
            sle.item_code AS item_code,
            SUM(sle.actual_qty) AS balance_qty,
            MAX(i.custom_moci_category) AS moci_category,
            MAX(i.custom_unit_weight_in_tone) AS unit_ton
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabItem` i ON i.name = sle.item_code
        WHERE
            sle.is_cancelled = 0
            AND sle.company = %(company)s
            AND sle.posting_date <= %(as_on_date)s
        GROUP BY sle.item_code
        HAVING balance_qty != 0
        """,
        {"company": company, "as_on_date": as_on_date},
        as_dict=True,
    )

    for r in rows:
        balance_qty = flt(r.get("balance_qty"))
        unit_ton = flt(r.get("unit_ton"))  # tons per 1 default UOM (your field)
        category = r.get("moci_category")

        ton_qty = balance_qty * unit_ton

        if category in totals_by_category:
            totals_by_category[category] += ton_qty
        else:
            # Items without category, or category not under MOCI parent
            uncategorized_total += ton_qty

    # 3) Build report rows: show ALL categories even if 0
    data = []
    for c in categories:
        data.append({
            "moci_category": c,
            "total_ton_qty": flt(totals_by_category.get(c)),
        })

    # Optional: show Uncategorized if it exists
    if flt(uncategorized_total) != 0:
        data.append({
            "moci_category": _("Uncategorized / Not under MoCI"),
            "total_ton_qty": flt(uncategorized_total),
        })

    return data
