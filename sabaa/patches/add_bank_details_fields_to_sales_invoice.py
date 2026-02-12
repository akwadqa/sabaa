import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():  
    custom_fields = {  
        "Sales Invoice": [  
            {  
                "fieldname": "custom_include_bank_details",  
                "label": _("Include Bank Details"),  
                "fieldtype": "Check",  
                "insert_after": "payments",  
                "module": "Sabaa",  
            },  
            {  
                "fieldname": "custom_bank_details",  
                "label": _("Bank Details"),  
                "fieldtype": "Text",  
                "depends_on": "eval:doc.custom_include_bank_details == 1",  
                "insert_after": "custom_include_bank_details",
                "translatable": 1,
                "module": "Sabaa",
                "default": """BANK DETAILS – SABA TRADING GROUP  
  
                Account Name: SABA TRADING GROUP  
                Bank Name: QIB – Qatar Islamic Bank  
                Branch Address: QIB Corporate Branch, P.O. Box 559, Doha, Qatar  
                Bank Account No.: 0110344260017  
                IBAN No.: QA22QISB0000000000110344260017  
                SWIFT Code: QISBQAQAXXX  
                
                FAWRAN DETAILS  
                
                Beneficiary Alias Name: CR-33971  
                Beneficiary Name: SABA TRADING GROUP  
                
                We appreciate your continued support and cooperation."""  
            }    
        ],    
    }    
              
  
    create_custom_fields(custom_fields, ignore_validate=True)  
    frappe.db.commit()