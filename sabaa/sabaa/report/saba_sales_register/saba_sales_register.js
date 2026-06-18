//  Copyright (c) 2026, Akwad Programming and contributors
//  For license information, please see license.txt


frappe.query_reports["Saba Sales Register"] = {
	onload(report) {
		const custom_title = __("Sales Register");
		report.page.set_title(custom_title);

		const orig_print = report.print_report.bind(report);
		report.print_report = async function (print_settings) {
			const saved = report.report_name;
			report.report_name = custom_title;
			try { await orig_print(print_settings); }
			finally { report.report_name = saved; }
		};

		const orig_pdf = report.pdf_report.bind(report);
		report.pdf_report = async function (print_settings) {
			const saved = report.report_name;
			report.report_name = custom_title;
			try { await orig_pdf(print_settings); }
			finally { report.report_name = saved; }
		};
	},
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			width: "80",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "mode_of_payment",
			label: __("Mode of Payment"),
			fieldtype: "Link",
			options: "Mode of Payment",
		},
		{
			fieldname: "owner",
			label: __("Owner"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "brand",
			label: __("Brand"),
			fieldtype: "Link",
			options: "Brand",
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "include_payments",
			label: __("Show Ledger View"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "include_returns",
			label: __("Include Returns"),
			fieldtype: "Check",
			default: 0
		}
	],
};

erpnext.utils.add_dimensions("Saba Sales Register", 7);
