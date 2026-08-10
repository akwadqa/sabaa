import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _


def execute():
    custom_fields = {
        "Sales Invoice Item": [
            {
                "fieldname": "custom_excise_rate",
                "label": _("Excise Rate"),
                "fieldtype": "Float",
                "insert_after": "net_amount",
                "module": "Sabaa",
                "precision": "4",
                "read_only": 1,
                "print_hide": 1,
                "description": _(
                    "Snapshot of the Item's Excise Amount (per Default UOM) at the time this row was added."
                ),
            },
            {
                "fieldname": "custom_excise_amount",
                "label": _("Excise Amount"),
                "fieldtype": "Currency",
                "insert_after": "custom_excise_rate",
                "module": "Sabaa",
                "options": "currency",
                "read_only": 1,
                "print_hide": 1,
            },
        ],
        "Sales Invoice": [
            {
                "fieldname": "custom_total_excise",
                "label": _("Total Excise"),
                "fieldtype": "Currency",
                "insert_after": "total_taxes_and_charges",
                "module": "Sabaa",
                "options": "currency",
                "read_only": 1,
                "print_hide": 1,
                "no_copy": 1,
            },
        ],
    }

    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()
