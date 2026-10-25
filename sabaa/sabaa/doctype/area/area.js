// Copyright (c) 2025, Akwad Programming and contributors
// For license information, please see license.txt

frappe.ui.form.on("Area", {
	refresh(frm) {
		frm.set_query("parent_area", () => {
			return {
				filters: {
					is_group: 1,
				},
			};
		});
	},
});
