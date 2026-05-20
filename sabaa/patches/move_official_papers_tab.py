from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    try:
        custom_fields = {
            "Employee": [
                {
                    "fieldname": "official_papers_tab",
                    "label": _("Official Papers"),
                    "fieldtype": "Tab Break",
                    "insert_after": "grade",
                    "module": "Sabaa"
                },
            ],
        }
    
        create_custom_fields(custom_fields, ignore_validate=True, update=True)
    

    except Exception:
        frappe.log_error("Patch Error: Add Custom Fields", frappe.get_traceback())
        raise  