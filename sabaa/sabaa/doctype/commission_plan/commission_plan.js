// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commission Plan", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("New rule"), () => new_rule_dialog(frm));
		frm.add_custom_button(__("Check setup"), () => frappe.set_route("commission-setup"));
	},
});

async function new_rule_dialog(frm) {
	const { message: templates } = await frappe.call("sabaa.sabaa.commission.api.get_templates");
	const options = templates.map((t) => ({ value: t.name, label: `${t.category} — ${t.role_label}` }));
	const dialog = new frappe.ui.Dialog({
		title: __("New rule"),
		fields: [
			{ fieldname: "template", label: __("Start from"), fieldtype: "Select", options, reqd: 1 },
			{ fieldname: "rule_name", label: __("Rule name"), fieldtype: "Data", description: __("Leave empty to use the template name.") },
		],
		primary_action_label: __("Create"),
		primary_action: async (values) => {
			const { message } = await frappe.call("sabaa.sabaa.commission.api.create_rule_from_template", { plan: frm.doc.name, ...values });
			dialog.hide();
			frappe.set_route("Form", "Commission Rule", message);
		},
	});
	dialog.show();
}
