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
            "fieldname": "total_qty",
            "label": _("Current Qty"),
            "fieldtype": "Data",
            "width": 180,
        },
    ]


def get_data(company, as_on_date):
    # 1) Get all MoCI categories
    categories = frappe.get_all(
        "Item Group",
        filters={"parent_item_group": MOCI_PARENT_GROUP},
        pluck="name",
        order_by="name",
    )

    totals_by_category = {
        c: {"kg": 0.0, "l": 0.0} for c in categories
    }

    uncategorized = {"kg": 0.0, "l": 0.0}

    # 2) Fetch balance qty + weight info
    rows = frappe.db.sql(
        """
        SELECT
            sle.item_code AS item_code,
            SUM(sle.actual_qty) AS balance_qty,
            MAX(i.custom_moci_category) AS moci_category,
            MAX(i.weight_uom) AS weight_uom,
            MAX(i.weight_per_unit) AS weight_per_unit
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

    # 3) Accumulate per category
    for r in rows:
        balance_qty = flt(r.get("balance_qty"))
        category = r.get("moci_category")
        weight_uom = r.get("weight_uom")
        weight_per_unit = flt(r.get("weight_per_unit"))

        total_weight = balance_qty * weight_per_unit

        target = totals_by_category.get(category) or uncategorized

        if weight_uom == "Gram":
            target["kg"] += total_weight / 1000
        elif weight_uom == "Milliliter":
            target["l"] += total_weight / 1000

    # 4) Build display rows (single column with labels)
    data = []

    for c in categories:
        kg = flt(totals_by_category[c]["kg"], 3)
        l = flt(totals_by_category[c]["l"], 3)

        parts = []
        if kg:
            parts.append(f"{kg} Kg")
        if l:
            parts.append(f"{l} L")

        data.append({
            "moci_category": c,
            "total_qty": " / ".join(parts) if parts else "0",
        })

    # Optional: Uncategorized
    if uncategorized["kg"] or uncategorized["l"]:
        parts = []
        if uncategorized["kg"]:
            parts.append(f"{flt(uncategorized['kg'], 3)} Kg")
        if uncategorized["l"]:
            parts.append(f"{flt(uncategorized['l'], 3)} L")

        data.append({
            "moci_category": _("Uncategorized / Not under MoCI"),
            "total_qty": " / ".join(parts),
        })

    return data
