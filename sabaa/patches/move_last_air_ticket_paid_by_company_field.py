import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    try:
        custom_fields = {
            "Employee": [
                {
                    "fieldname": "last_air_ticket_paid_by_company",
                    "label": _("Last Air Ticket Paid By Company"),
                    "fieldtype": "Check",
                    "insert_after": "end_of_service_benefit_paid",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "column_7_official_papers",
                    "fieldtype": "Column Break",
                    "insert_after": "last_air_ticket_paid_by_company",
                    "module": "Sabaa"
                },
            ],
        }

        create_custom_fields(custom_fields, ignore_validate=True, update=True)
    

    except Exception:
        frappe.log_error("Patch Error: Add Custom Fields", frappe.get_traceback())
        raise