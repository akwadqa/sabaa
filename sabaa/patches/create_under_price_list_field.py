import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    custom_fields = {
        "Sales Invoice": [
            {
                "fieldname": "under_price_list_rate_detected",
                "label": _("Under Price List"),
                "fieldtype": "Check",
                "insert_after": "total_qty",
                "module": "Sabaa",
                "read_only": 1,
            }
        ],
    }

    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()

    frappe.log_error("Adding under price list field patch executed successfully", "Patch Log")
