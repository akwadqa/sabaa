import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute(): 
    try: 
        custom_fields = {  
            "Company": [  
                {  
                    "fieldname": "sales_collection_accounts",  
                    "label": _("Sales Collection Accounts"),  
                    "fieldtype": "Table MultiSelect",  
                    "options": "Sales Collection Account",
                    "insert_after": "default_finance_book",  
                    "module": "Sabaa",  
                },    
            ],    
        }    
                
    
        create_custom_fields(custom_fields, ignore_validate=True, update=True)  
    
    except Exception:
        frappe.log_error("Failed to create custom field", frappe.get_traceback())