// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.query_reports["Trading Gross Profit"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
			reqd: 1,
		},
		{
			fieldname: "sales_invoice",
			label: __("Sales Invoice"),
			fieldtype: "Link",
			options: "Sales Invoice",
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options:
				"Invoice\nItem Code\nItem Group\nBrand\nWarehouse\nCustomer\nCustomer Group\nTerritory\nSales Person\nProject\nCost Center\nMonthly\nPayment Term",
			default: "Invoice",
			on_change: function () {
				toggle_invoice_filters();
				frappe.query_report.refresh(); 
			},
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "sales_person",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: function () {
				var company = frappe.query_report.get_filter_value("company");
				return {
					filters: [["Warehouse", "company", "=", company]],
				};
			},
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			options: "Cost Center",
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "MultiSelectList",
			options: "Project",
			get_data: function (txt) {
				return frappe.db.get_link_options("Project", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			"fieldname": "invoice_type",
			"label": __("Invoice Type"),
			"fieldtype": "Select",
			"options": "All Invoices\nSales Invoice\nReturn Invoice",
			"default": "All Invoices"
		},
		{
			fieldname: "include_returned_invoices",
			label: __("Include Returned Invoices (Stand-alone)"),
			fieldtype: "Check",
			default: 1,
			depends_on: "eval: frappe.query_report.get_filter_value('invoice_type') == 'All Invoices'"

		},
	],
	tree: true,
	name_field: "parent",
	parent_field: "parent_invoice",
	initial_depth: 3,
	formatter: function (value, row, column, data, default_formatter) {
		if (column.fieldname == "sales_invoice" && column.options == "Item" && data && data.indent == 0) {
			column._options = "Sales Invoice";
		} else {
			column._options = "";
		}
		value = default_formatter(value, row, column, data);

		if (data && (data.indent == 0.0 || (row[1] && row[1].content == "Total"))) {
			value = $(`<span>${value}</span>`);
			var $value = $(value).css("font-weight", "bold");
			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
};

function toggle_invoice_filters() {
	const group_by = frappe.query_report.get_filter_value("group_by");
	const is_invoice = group_by === "Invoice";

	const filters_to_toggle = ["cost_center", "project", "vehicle"];

	filters_to_toggle.forEach(fieldname => {
		const filter = frappe.query_report.get_filter(fieldname);
		if (!filter) return;

		// Hide or show
		filter.df.hidden = is_invoice ? 1 : 0;

		// Clear value only when switching to Invoice
		if (is_invoice) {
			frappe.query_report.set_filter_value(fieldname, []);
		}

		filter.refresh();
	});
}

// Run on load
frappe.query_reports["Trading Gross Profit"].onload = function () {
	toggle_invoice_filters();
};

erpnext.utils.add_dimensions("Trading Gross Profit", 15);
