import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    try:
        custom_fields = {
            "Sales Person": [
                {
                    "fieldname": "custom_assigned_area",
                    "label": _("Assigned Area"),
                    "fieldtype": "Link",
                    "options": "Area",
                    "insert_after": "enabled",
                    "module": "Sabaa"
                },
            ],
        }

        create_custom_fields(custom_fields, ignore_validate=True, update=True)

        client_script_name = "Sales Person Assigned Area Filter"
        script = """frappe.ui.form.on("Sales Person", {
	refresh(frm) {
		frm.set_query("custom_assigned_area", () => {
			return {
				filters: {
					is_group: 0,
				},
			};
		});
	},
});
"""

        if frappe.db.exists("Client Script", client_script_name):
            doc = frappe.get_doc("Client Script", client_script_name)
            doc.script = script
            doc.dt = "Sales Person"
            doc.view = "Form"
            doc.enabled = 1
            doc.save()
        else:
            frappe.get_doc({
                "doctype": "Client Script",
                "name": client_script_name,
                "dt": "Sales Person",
                "view": "Form",
                "enabled": 1,
                "script": script,
            }).insert()

    except Exception:
        frappe.log_error("Patch Error: Add Assigned Area Field To Sales Person", frappe.get_traceback())
        raise
