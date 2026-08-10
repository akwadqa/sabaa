// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Reference", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.is_current) return;

		frm.add_custom_button(__("Renew"), () => {
			frm.call("make_renewal").then((r) => {
				if (r.message) {
					frappe.set_route("Form", "Employee Reference", r.message);
				}
			});
		});
	},
});
