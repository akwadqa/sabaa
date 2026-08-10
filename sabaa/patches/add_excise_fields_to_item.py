import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _


def execute():
    custom_fields = {
        "Item": [
            {
                "fieldname": "custom_excise_section",
                "label": _("Excise Tax"),
                "fieldtype": "Section Break",
                "insert_after": "taxes",
                "module": "Sabaa",
                "collapsible": 1,
            },
            {
                "fieldname": "custom_is_excisable",
                "label": _("Is Excisable"),
                "fieldtype": "Check",
                "insert_after": "custom_excise_section",
                "module": "Sabaa",
                "description": _(
                    "If checked, Excise Tax Recoverable is calculated item-wise on Sales Invoices for this Item."
                ),
            },
            {
                "fieldname": "custom_excise_rate",
                "label": _("Excise Amount (per Default UOM)"),
                "fieldtype": "Currency",
                "insert_after": "custom_is_excisable",
                "module": "Sabaa",
                "precision": "4",
                "depends_on": "eval:doc.custom_is_excisable",
                "mandatory_depends_on": "eval:doc.custom_is_excisable",
                "description": _(
                    "Fixed Excise amount charged per unit of this Item's Default Unit of Measure (Stock UOM)."
                ),
            },
        ],
    }

    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()
