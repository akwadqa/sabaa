import frappe

def calculate_total_gross_weight(doc, method):

    total_weight = 0

    for row in doc.items:
        gw = frappe.db.get_value(
            "Item",
            row.item_code,
            "custom_gross_weight_per_unit"
        )

        if gw:
            total_weight += (gw * (row.qty or 1))

    doc.custom_total_gross_weight = total_weight
