import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _


def execute():
    custom_fields = {
        "Company": [
            {
                "fieldname": "custom_excise_tax_recoverable_account",
                "label": _("Excise Tax Recoverable Account"),
                "fieldtype": "Link",
                "options": "Account",
                "insert_after": "default_receivable_account",
                "module": "Sabaa",
                "description": _(
                    "Asset account used to track Excise Tax paid to Customs and recovered "
                    "from customers through Sales Invoices. Required for Companies that sell "
                    "Excisable Items."
                ),
            },
        ],
    }

    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()
