import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    custom_fields = {
        "Expense Entry Detail": [
            {
                "fieldname": "expense_date",
                "label": _("Expense Date"),
                "fieldtype": "Date",
                "insert_after": "expense_account",
                "module": "Sabaa",
                "in_list_view": 1,
                "reqd": 1,
                "in_standard_filter": 1
            }
        ],
    }

    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()