import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    doctypes = [
        "Purchase Order",
        "Purchase Invoice",
        "Sales Invoice",
        "Delivery Note",
    ]

    custom_fields = {}

    for doctype in doctypes:
        custom_fields.setdefault(doctype, []).append(
            {
                "fieldname": "total_qty_by_uom",
                "label": "Total Quantity (By UOM)",
                "fieldtype": "Text",
                "read_only": 1,
                "insert_after": "total_qty",
                "module": "Sabaa"
            }
        )

    create_custom_fields(custom_fields, ignore_validate=True)

    frappe.db.commit()