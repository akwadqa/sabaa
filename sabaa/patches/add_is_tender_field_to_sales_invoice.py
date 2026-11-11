from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	custom_fields = {
		"Sales Invoice": [
			{
				"fieldname": "is_tender",
				"label": _("Tender Sale"),
				"fieldtype": "Check",
				"insert_after": "customer",
				"allow_on_submit": 0,
				"module": "Sabaa",
			},
		],
	}
	create_custom_fields(custom_fields, ignore_validate=True, update=True)
