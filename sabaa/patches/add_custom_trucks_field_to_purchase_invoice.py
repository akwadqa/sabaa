import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    custom_fields = {
        "Purchase Invoice": [
            {
                "fieldname": "custom_trucks",
                "label": _("Trucks"),
                "fieldtype": "Int",
                "insert_after": "company",
                "module": "Sabaa",
                "non_negative": 1,
            }
        ],
    }

    create_custom_fields(custom_fields, ignore_validate=True)
