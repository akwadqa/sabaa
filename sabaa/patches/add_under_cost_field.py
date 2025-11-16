import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    custom_fields = {
        "Sales Order": [
            {
                "fieldname": "under_cost_detected",
                "label": _("Under Cost"),
                "fieldtype": "Check",
                "insert_after": "total_qty",
                "module": "Sabaa",
            }
        ]
    }

    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()

    frappe.log_error("Sales Order patch executed successfully", "Patch Log")
