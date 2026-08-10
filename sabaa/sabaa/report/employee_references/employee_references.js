// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.query_reports["Employee References"] = {
	"filters": [
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			reqd: 1,
		},
		{
			fieldname: "document",
			label: __("Document"),
			fieldtype: "Select",
			options: ["", "QID", "Passport", "Health Insurance", "Driving License", "Contract"],
		},
		{
			fieldname: "show_current_only",
			label: __("Show Current Only"),
			fieldtype: "Check",
			default: 1,
		},
	],
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},
	onload(report) {
		report.page.add_inner_button(__("Add"), () => {
			const employee = frappe.query_report.get_filter_value("employee");
			frappe.new_doc("Employee Reference", { employee });
		}, null, "primary");

		report.page.add_inner_button(__("Renew"), () => {
			const indexes = frappe.query_report.datatable.rowmanager.getCheckedRows();

			if (!indexes || indexes.length === 0) {
				frappe.msgprint(__("Select a reference row to renew."));
				return;
			}

			if (indexes.length > 1) {
				frappe.msgprint(__("Select only one row to renew at a time."));
				return;
			}

			const row = frappe.query_report.data[indexes[0]];

			if (!row) {
				return;
			}

			if (!row.is_current) {
				frappe.msgprint(__("Only the current reference for a document can be renewed."));
				return;
			}

			frappe.confirm(
				__("Renew {0}? This will create a new reference and mark this one as replaced.", [row.name]),
				() => {
					frappe.call({
						method: "sabaa.sabaa.doctype.employee_reference.employee_reference.renew_reference",
						args: { reference: row.name },
						freeze: true,
						callback(r) {
							if (r.message) {
								frappe.set_route("Form", "Employee Reference", r.message);
							}
						},
					});
				}
			);
		});
	},
};
