from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Customer Group": [
				{
					"fieldname": "custom_print_stamp_on_invoice",
					"label": _("Print Stamp on Invoice"),
					"fieldtype": "Check",
					"insert_after": "is_group",
					"description": _("Print the company stamp on submitted Sales Invoices of this group."),
					"module": "Sabaa",
				},
			],
			"App Settings": [
				{
					"fieldname": "custom_invoice_stamp_section",
					"label": _("Invoice Stamp"),
					"fieldtype": "Section Break",
					"insert_after": "so_print_format",
					"description": _(
						"Upload transparent PNG files as public files. The stamp prints on submitted Sales "
						"Invoices of customer groups with Print Stamp on Invoice ticked."
					),
					"module": "Sabaa",
				},
				{
					"fieldname": "custom_saba_invoice_stamp",
					"label": _("Saba Stamp"),
					"fieldtype": "Attach Image",
					"insert_after": "custom_invoice_stamp_section",
					"module": "Sabaa",
				},
				{
					"fieldname": "custom_green_world_invoice_stamp",
					"label": _("Green World Stamp"),
					"fieldtype": "Attach Image",
					"insert_after": "custom_saba_invoice_stamp",
					"module": "Sabaa",
				},
			],
		},
		ignore_validate=True,
		update=True,
	)
