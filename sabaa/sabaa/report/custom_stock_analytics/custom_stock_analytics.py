import datetime

import frappe
from frappe import _, scrub
from frappe.query_builder.functions import CombineDatetime
from frappe.utils import get_datetime, get_first_day_of_week, get_quarter_start, getdate
from frappe.utils import get_first_day as get_first_day_of_month
from frappe.utils.nestedset import get_descendants_of

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter
from erpnext.stock.utils import is_reposting_item_valuation_in_progress


def execute(filters=None):
    is_reposting_item_valuation_in_progress()
    filters = frappe._dict(filters or {})
    columns = get_columns(filters)
    data = get_data(filters)

    chart = get_chart_data(columns) if filters.get("value_quantity") == "Value" else None

    return columns, data, None, chart


def get_columns(filters):
    columns = [
        {"label": _("Item"), "options": "Item", "fieldname": "name", "fieldtype": "Link", "width": 140},
        {
            "label": _("Item Name"),
            "options": "Item",
            "fieldname": "item_name",
            "fieldtype": "Link",
            "width": 140,
        },
        {
            "label": _("Item Group"),
            "options": "Item Group",
            "fieldname": "item_group",
            "fieldtype": "Link",
            "width": 140,
        },
        {"label": _("Brand"), "fieldname": "brand", "fieldtype": "Data", "width": 120},
        {"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 120},
        {"label": _("Barcode"), "fieldname": "barcode", "fieldtype": "Data", "width": 180},
    ]

    ranges = get_period_date_ranges(filters)
    period_fieldtype = "Float" if filters.get("value_quantity") == "Value" else "Data"

    for _dummy, end_date in ranges:
        period = get_period(end_date, filters)
        columns.append(
            {
                "label": _(period),
                "fieldname": scrub(period),
                "fieldtype": period_fieldtype,
                "width": 120,
            }
        )

    return columns


def get_period_date_ranges(filters):
    from dateutil.relativedelta import relativedelta

    from_date = round_down_to_nearest_frequency(filters.from_date, filters.range)
    to_date = getdate(filters.to_date)

    increment = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Yearly": 12}.get(filters.range, 1)

    periodic_daterange = []
    for _dummy in range(1, 53, increment):
        if filters.range == "Weekly":
            period_end_date = from_date + relativedelta(days=6)
        else:
            period_end_date = from_date + relativedelta(months=increment, days=-1)

        if period_end_date > to_date:
            period_end_date = to_date
        periodic_daterange.append([from_date, period_end_date])

        from_date = period_end_date + relativedelta(days=1)
        if period_end_date == to_date:
            break

    return periodic_daterange


def round_down_to_nearest_frequency(date: str, frequency: str) -> datetime.datetime:

    def _get_first_day_of_fiscal_year(date):
        fiscal_year = get_fiscal_year(date)
        return fiscal_year and fiscal_year[1] or date

    round_down_function = {
        "Monthly": get_first_day_of_month,
        "Quarterly": get_quarter_start,
        "Weekly": get_first_day_of_week,
        "Yearly": _get_first_day_of_fiscal_year,
    }.get(frequency, getdate)
    return round_down_function(date)


def get_period(posting_date, filters):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    if filters.range == "Weekly":
        period = _("Week {0} {1}").format(str(posting_date.isocalendar()[1]), str(posting_date.year))
    elif filters.range == "Monthly":
        period = _(str(months[posting_date.month - 1])) + " " + str(posting_date.year)
    elif filters.range == "Quarterly":
        period = _("Quarter {0} {1}").format(str(((posting_date.month - 1) // 3) + 1), str(posting_date.year))
    else:
        year = get_fiscal_year(posting_date, company=filters.company)
        period = str(year[2])

    return period


def get_periodic_data(entry, filters):
    expected_ranges = get_period_date_ranges(filters)
    expected_periods = []
    for _start_date, end_date in expected_ranges:
        expected_periods.append(get_period(end_date, filters))

    periodic_data = {}
    for d in entry:
        period = get_period(d.posting_date, filters)
        bal_qty = 0

        fill_intermediate_periods(periodic_data, d.item_code, period, expected_periods)

        if periodic_data.get(d.item_code) and not periodic_data.get(d.item_code).get(period):
            previous_balance = periodic_data[d.item_code]["balance"].copy()
            periodic_data[d.item_code][period] = previous_balance

        if d.voucher_type == "Stock Reconciliation" and not d.batch_no:
            if periodic_data.get(d.item_code) and periodic_data.get(d.item_code).get("balance").get(
                d.warehouse
            ):
                bal_qty = periodic_data[d.item_code]["balance"][d.warehouse]

            qty_diff = d.qty_after_transaction - bal_qty
        else:
            qty_diff = d.actual_qty

        if filters["value_quantity"] == "Quantity":
            value = qty_diff
        else:
            value = d.stock_value_difference

        periodic_data.setdefault(d.item_code, {}).setdefault("balance", {}).setdefault(d.warehouse, 0.0)
        periodic_data.setdefault(d.item_code, {}).setdefault(period, {}).setdefault(d.warehouse, 0.0)

        periodic_data[d.item_code]["balance"][d.warehouse] += value
        periodic_data[d.item_code][period][d.warehouse] = periodic_data[d.item_code]["balance"][d.warehouse]

    return periodic_data


def fill_intermediate_periods(
    periodic_data, item_code: str, current_period: str, all_periods: list[str]
) -> None:
    previous_period_data = None
    for period in all_periods:
        if period == current_period:
            return

        if (
            periodic_data.get(item_code)
            and not periodic_data.get(item_code).get(period)
            and previous_period_data
        ):
            periodic_data[item_code][period] = previous_period_data.copy()

        previous_period_data = periodic_data.get(item_code, {}).get(period)


def get_data(filters):
    data = []
    items = get_items(filters)
    sle = get_stock_ledger_entries(filters, items)
    item_details = get_item_details(items, sle)
    periodic_data = get_periodic_data(sle, filters)
    ranges = get_period_date_ranges(filters)

    item_uom_map = get_item_uom_map(list(item_details.keys()))
    item_barcode_map = get_item_barcode_map(list(item_details.keys()))

    today = getdate()

    for _dummy, item_data in item_details.items():
        row = {
            "name": item_data.name,
            "item_name": item_data.item_name,
            "item_group": item_data.item_group,
            "uom": item_data.stock_uom,
            "brand": item_data.brand,
            "barcode": "",
        }

        # Barcode depends on the UOMs (big UOM + stock UOM if available)
        uom_rows = item_uom_map.get(item_data.name) or []
        big_uom = None
        for r in uom_rows:
            if r.conversion_factor and r.conversion_factor > 1:
                if not big_uom or r.conversion_factor > big_uom.conversion_factor:
                    big_uom = r

        barcodes = item_barcode_map.get(item_data.name) or {}
        barcode_parts = []

        if big_uom:
            b = (barcodes.get(big_uom.uom) or "").strip()
            if b:
                barcode_parts.append(f"{big_uom.uom}: {b}")

        b_stock = (barcodes.get(item_data.stock_uom) or "").strip()
        if b_stock:
            barcode_parts.append(f"{item_data.stock_uom}: {b_stock}")

        if not barcode_parts:
            fallback = (barcodes.get("__first__") or "").strip()
            if fallback:
                barcode_parts.append(fallback)

        row["barcode"] = " | ".join(barcode_parts)

        previous_period_value = 0.0

        for start_date, end_date in ranges:
            period = get_period(end_date, filters)
            key = scrub(period)
            period_data = periodic_data.get(item_data.name, {}).get(period)

            if period_data:
                numeric_value = previous_period_value = sum(period_data.values())
            else:
                numeric_value = previous_period_value if today >= start_date else None

            row[key] = numeric_value

        if filters.get("value_quantity") == "Quantity":
            for _start_date, end_date in ranges:
                period = get_period(end_date, filters)
                key = scrub(period)
                qty_value = row.get(key)

                if qty_value is None:
                    continue

                row[key] = format_qty_with_uom_breakdown(
                    item_code=item_data.name,
                    stock_uom=item_data.stock_uom,
                    qty=qty_value,
                    item_uom_map=item_uom_map,
                )

        data.append(row)

    return data


def get_chart_data(columns):
    labels = [d.get("label") for d in columns[6:]]
    chart = {"data": {"labels": labels, "datasets": []}}
    chart["type"] = "line"

    return chart


def get_items(filters):
    "Get items based on item code, item group or brand."
    if item_code := filters.get("item_code"):
        return [item_code]
    else:
        item_filters = {"is_stock_item": 1}
        if item_group := filters.get("item_group"):
            children = get_descendants_of("Item Group", item_group, ignore_permissions=True)
            item_filters["item_group"] = ("in", [*children, item_group])
        if brand := filters.get("brand"):
            item_filters["brand"] = brand

        return frappe.get_all("Item", filters=item_filters, pluck="name", order_by=None)


def get_stock_ledger_entries(filters, items):
    sle = frappe.qb.DocType("Stock Ledger Entry")

    query = (
        frappe.qb.from_(sle)
        .select(
            sle.item_code,
            sle.warehouse,
            sle.posting_date,
            sle.actual_qty,
            sle.valuation_rate,
            sle.company,
            sle.voucher_type,
            sle.qty_after_transaction,
            sle.stock_value_difference,
            sle.item_code.as_("name"),
            sle.voucher_no,
            sle.stock_value,
            sle.batch_no,
        )
        .where((sle.docstatus < 2) & (sle.is_cancelled == 0))
        .orderby(sle.posting_datetime)
        .orderby(sle.creation)
    )

    if items:
        query = query.where(sle.item_code.isin(items))

    query = apply_conditions(query, filters)
    return query.run(as_dict=True)


def apply_conditions(query, filters):
    sle = frappe.qb.DocType("Stock Ledger Entry")
    warehouse_table = frappe.qb.DocType("Warehouse")

    if not filters.get("from_date"):
        frappe.throw(_("'From Date' is required"))

    if to_date := filters.get("to_date"):
        to_date = get_datetime(str(to_date) + " 23:59:59")
        query = query.where(sle.posting_datetime <= to_date)
    else:
        frappe.throw(_("'To Date' is required"))

    if company := filters.get("company"):
        query = query.where(sle.company == company)

    if filters.get("warehouse"):
        query = apply_warehouse_filter(query, sle, filters)
    elif warehouse_type := filters.get("warehouse_type"):
        query = (
            query.join(warehouse_table)
            .on(warehouse_table.name == sle.warehouse)
            .where(warehouse_table.warehouse_type == warehouse_type)
        )

    return query


def get_item_details(items, sle):
    item_details = {}
    if not items:
        items = list(set(d.item_code for d in sle))

    if not items:
        return item_details

    item_table = frappe.qb.DocType("Item")

    query = (
        frappe.qb.from_(item_table)
        .select(
            item_table.name,
            item_table.item_name,
            item_table.description,
            item_table.item_group,
            item_table.brand,
            item_table.stock_uom,
        )
        .where(item_table.name.isin(items))
    )

    result = query.run(as_dict=1)

    for item_row in result:
        item_details.setdefault(item_row.name, item_row)

    return item_details


# ---------- NEW HELPERS FOR UOM BREAKDOWN ----------


def get_item_uom_map(item_codes):
    if not item_codes:
        return {}

    rows = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": ("in", item_codes)},
        fields=["parent", "uom", "conversion_factor"],
        order_by="conversion_factor desc",
    )

    uom_map = {}
    for r in rows:
        uom_map.setdefault(r.parent, []).append(r)

    return uom_map


def format_qty_with_uom_breakdown(item_code, stock_uom, qty, item_uom_map):

    if qty is None:
        return ""

    try:
        qty_int = int(round(qty))
    except Exception:
        return f"{qty} {stock_uom}"

    uom_rows = item_uom_map.get(item_code) or []

    big_uom = None
    for r in uom_rows:
        if r.conversion_factor and r.conversion_factor > 1:
            if not big_uom or r.conversion_factor > big_uom.conversion_factor:
                big_uom = r

    if not big_uom:
        return f"{qty_int} {stock_uom}"

    factor = int(big_uom.conversion_factor)
    if factor <= 1:
        return f"{qty_int} {stock_uom}"

    big_qty = qty_int // factor
    remainder = qty_int % factor

    parts = []
    if big_qty:
        parts.append(f"{big_qty} {big_uom.uom}")
    if remainder:
        parts.append(f"{remainder} {stock_uom}")
    if not parts:
        parts.append(f"0 {stock_uom}")

    return ", ".join(parts)


# ---------- NEW HELPERS FOR BARCODE BY UOM ----------


def get_item_barcode_map(item_codes):
    """
    Return:
      { item_code: { uom: barcode, '__first__': first_barcode } }
    from the Item Barcode child table.
    """
    if not item_codes:
        return {}

    rows = frappe.get_all(
        "Item Barcode",
        filters={"parent": ("in", item_codes)},
        fields=["parent", "barcode", "uom", "idx"],
        order_by="parent asc, idx asc",
    )

    out = {}
    for r in rows:
        item_code = r.parent
        barcode = (r.barcode or "").strip()
        uom = (r.uom or "").strip()

        if not barcode:
            continue

        out.setdefault(item_code, {})

        if "__first__" not in out[item_code]:
            out[item_code]["__first__"] = barcode

        if uom and uom not in out[item_code]:
            out[item_code][uom] = barcode

    return out
