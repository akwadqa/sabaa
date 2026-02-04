import frappe

def execute():
    doctypes = [
        "Purchase Order",
        "Purchase Invoice",
        "Sales Invoice",
        "Delivery Note",
    ]

    for doctype in doctypes:
        frappe.db.set_value(
            "DocField",
            {
                "parent": doctype,
                "fieldname": "total_qty",
            },
            {
                "hidden": 1,
            },
        )

