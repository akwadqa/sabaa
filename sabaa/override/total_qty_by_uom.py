import frappe
from frappe.utils import flt


def calculate_total_qty_by_uom(doc, method=None):
    UOM_ORDER = ["Ctn", "Box", "Set", "Outer", "Pcs"]

    # Step 1: sum each item's qty (converted to its stock UOM) across all rows,
    # so multiple lines of the same item accumulate before we re-split into UOMs.
    item_stock_qty = {}
    for row in doc.items:
        if not row.item_code or not row.qty:
            continue

        stock_qty = flt(row.stock_qty) or flt(row.qty) * (flt(row.conversion_factor) or 1)
        item_stock_qty[row.item_code] = item_stock_qty.get(row.item_code, 0) + stock_qty

    if not item_stock_qty:
        doc.total_qty_by_uom = ""
        return

    item_codes = list(item_stock_qty.keys())

    # Step 2: batch-fetch each item's stock UOM and its alternate UOM conversion factors.
    stock_uoms = dict(
        frappe.get_all(
            "Item",
            filters={"name": ["in", item_codes]},
            fields=["name", "stock_uom"],
            as_list=True,
        )
    )

    item_uom_factors = {
        item_code: ({stock_uoms[item_code]: 1.0} if stock_uoms.get(item_code) else {})
        for item_code in item_codes
    }

    for uom_row in frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": ["in", item_codes], "parenttype": "Item"},
        fields=["parent", "uom", "conversion_factor"],
    ):
        factor = flt(uom_row.conversion_factor)
        if factor > 0:
            item_uom_factors.setdefault(uom_row.parent, {})[uom_row.uom] = factor

    # Step 3: per item, greedily break its total stock qty into the largest
    # applicable UOMs first (based on that item's own conversion factors),
    # then add the resulting counts into the document-wide totals per UOM.
    uom_totals = {}

    for item_code, total_stock_qty in item_stock_qty.items():
        applicable = sorted(
            (
                (uom, factor)
                for uom, factor in item_uom_factors.get(item_code, {}).items()
                if uom in UOM_ORDER
            ),
            key=lambda pair: pair[1],
            reverse=True,
        )

        if not applicable:
            continue

        remaining = flt(total_stock_qty, 6)
        last_index = len(applicable) - 1

        for index, (uom, factor) in enumerate(applicable):
            if index == last_index:
                qty = flt(remaining / factor, 6)
            else:
                qty = int(remaining // factor)
                remaining -= qty * factor

            if qty:
                uom_totals[uom] = uom_totals.get(uom, 0) + qty

    formatted = []

    for uom in UOM_ORDER:
        if uom not in uom_totals:
            continue

        qty = round(uom_totals[uom], 4)
        qty_display = int(qty) if qty == int(qty) else qty
        formatted.append(f"{qty_display} {uom}")

    doc.total_qty_by_uom = ", ".join(formatted)