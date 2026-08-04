import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    try:
        custom_fields = {
            "Vehicle": [
                {
                    "fieldname": "vehicle_type",
                    "label": _("Type"),
                    "fieldtype": "Link",
                    "options": "Vehicle Type",
                    "insert_after": "model",
                    "translatable": 1,
                    "module": "Sabaa"
                },
            ],
        }

        create_custom_fields(custom_fields, ignore_validate=True, update=True)
    

    except Exception:
        frappe.log_error("Patch Error: Add Custom Fields", frappe.get_traceback())
        raise