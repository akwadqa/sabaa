import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    try:
        custom_fields = {
            "Employee": [
                {
                    "fieldname": "vehicle_type",
                    "label": _("Type"),
                    "fieldtype": "Data",
                    "fetch_from":"license_plate.vehicle_type",
                    "fetch_if_empty":1,
                    "insert_after": "license_plate",
                    "translatable": 1,
                    "module": "Sabaa"
                },
                {
                    "fieldname": "column_5_official_papers",
                    "fieldtype": "Column Break",
                    "insert_after": "vehicle_type",
                    "module": "Sabaa"
                },

            ],
        }

        create_custom_fields(custom_fields, ignore_validate=True, update=True)
    

    except Exception:
        frappe.log_error("Patch Error: Add Custom Fields", frappe.get_traceback())
        raise