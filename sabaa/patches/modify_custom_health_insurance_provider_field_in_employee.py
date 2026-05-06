import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    try:
        custom_fields = {
            "Employee": [
                {
                    "fieldname": "health_insurance_provider",
                    "label": _("Health Certificate"),
                    "fieldtype": "Link",
                    "options": "Employee Health Insurance",
                    "insert_after": "health_details",
                    "module": "Sabaa"
                },
            ],
        }

        create_custom_fields(custom_fields, ignore_validate=True, update=True)
    

    except Exception:
        frappe.log_error("Patch Error: Add Custom Fields", frappe.get_traceback())
        raise