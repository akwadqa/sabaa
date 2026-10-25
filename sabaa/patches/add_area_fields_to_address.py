import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    try:
        custom_fields = {
            "Address": [
                {
                    "fieldname": "custom_area_section",
                    "label": _("Area"),
                    "fieldtype": "Section Break",
                    "insert_after": "disabled",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "custom_area",
                    "label": _("Area"),
                    "fieldtype": "Link",
                    "options": "Area",
                    "reqd": 0,
                    "insert_after": "custom_area_section",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "custom_column_break_area",
                    "fieldtype": "Column Break",
                    "insert_after": "custom_area",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "custom_parent_area",
                    "label": _("Parent Area"),
                    "fieldtype": "Link",
                    "options": "Area",
                    "fetch_from": "custom_area.parent_area",
                    "read_only": 1,
                    "insert_after": "custom_column_break_area",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "custom_zone",
                    "label": _("Zone"),
                    "fieldtype": "Data",
                    "fetch_from": "custom_area.zone",
                    "read_only": 1,
                    "insert_after": "custom_parent_area",
                    "module": "Sabaa"
                },
            ],
        }

        create_custom_fields(custom_fields, ignore_validate=True, update=True)

        client_script_name = "Address Area Filter"
        script = """frappe.ui.form.on("Address", {
	refresh(frm) {
		frm.set_query("custom_area", () => {
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
            doc.dt = "Address"
            doc.view = "Form"
            doc.enabled = 1
            doc.save()
        else:
            frappe.get_doc({
                "doctype": "Client Script",
                "name": client_script_name,
                "dt": "Address",
                "view": "Form",
                "enabled": 1,
                "script": script,
            }).insert()

    except Exception:
        frappe.log_error("Patch Error: Add Area Fields To Address", frappe.get_traceback())
        raise
