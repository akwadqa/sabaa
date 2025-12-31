import frappe

@frappe.whitelist()
def get_item_uoms(item_code):   
    if not item_code:
        return []

    uoms = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": item_code},
        fields=["uom"]
    )

    if not uoms:
        item = frappe.get_doc("Item", item_code)
        return [item.stock_uom]

    return [d.uom for d in uoms]