import frappe

def calculate_total_qty_by_uom(doc, method=None):
    UOM_ORDER = ["Ctn", "Box", "Set", "Outer", "Pcs"]

    uom_totals = {}

    for row in doc.items:
        if not row.uom or not row.qty:
            continue

        if row.uom not in UOM_ORDER:
            continue

        uom_totals[row.uom] = uom_totals.get(row.uom, 0) + row.qty

    formatted = []

    for uom in UOM_ORDER:
        if uom not in uom_totals:
            continue

        qty = uom_totals[uom]
        qty_display = int(qty) if qty == int(qty) else qty
        formatted.append(f"{qty_display} {uom}")

    doc.total_qty_by_uom = ", ".join(formatted)