import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    custom_fields = {
        "Sales Invoice": [
            {
                "fieldname": "driver",
                "label": _("Driver"),
                "fieldtype": "Link",
                "options": "Driver",
                "insert_after": "po_date",
                "module": "Sabaa",
            },
            {
                "fieldname": "driver_name",
                "label": _("Driver Name"),
                "fieldtype": "Data",
                "insert_after": "driver",
                "module": "Sabaa",
            }
        ],
    }

    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()