// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.query_reports["Trading Sales Summary"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			width: "80",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			width: "80",
		},
		{
			fieldname: "group_by",
			label: __("Group By"),
			fieldtype: "Select",
			options: ["", "Sales Order", "Sales Invoice"],
			reqd: 1,
			width: "100",
			on_change: function () {
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "include_returns",
			label: __("Include Returns"),
			fieldtype: "Check",
			depends_on: "eval:doc.group_by=='Sales Order'",
			description: __("Also fetch standalone Return Sales Invoices for the same date/filters"),
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
			on_change: function () {
				frappe.query_report.set_filter_value("item", "");
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			get_query: function () {
				let item_group = frappe.query_report.get_filter_value("item_group");
				let filters = {};
				if (item_group) {
					filters["item_group"] = item_group;
				}
				return { filters: filters };
			},
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
			on_change: function () {
				frappe.query_report.set_filter_value("customer", "");
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			get_query: function () {
				let customer_group = frappe.query_report.get_filter_value("customer_group");
				let filters = {};
				if (customer_group) {
					filters["customer_group"] = customer_group;
				}
				return { filters: filters };
			},
		},
		{
			fieldname: "sales_person",
			label: __("Salesperson"),
			fieldtype: "Link",
			options: "Sales Person",
		},
		{
			fieldname: "zone_or_area",
			label: __("Zone / Area"),
			fieldtype: "Data",
		},
	],
	onload: function (report) {
		const style_id = "trading-sales-summary-style";
		if (!document.getElementById(style_id)) {
			const style = document.createElement("style");
			style.id = style_id;
			style.innerHTML = `
				.trading-sales-summary-cards .report-summary .summary-item {
					border-radius: var(--border-radius-md, 8px);
					padding: 8px 16px;
				}
				.trading-sales-summary-cards .report-summary .summary-item:nth-child(1) {
					background: #e8f1ff;
				}
				.trading-sales-summary-cards .report-summary .summary-item:nth-child(2) {
					background: #e9f9ef;
				}
				.trading-sales-summary-cards .report-summary .summary-item:nth-child(3) {
					background: #fff6dd;
				}
				.trading-sales-summary-cards .report-summary .summary-item:nth-child(4) {
					background: #fdeaf2;
				}
				[data-theme="dark"] .trading-sales-summary-cards .report-summary .summary-item:nth-child(1) {
					background: #1c2b42;
				}
				[data-theme="dark"] .trading-sales-summary-cards .report-summary .summary-item:nth-child(2) {
					background: #1c3324;
				}
				[data-theme="dark"] .trading-sales-summary-cards .report-summary .summary-item:nth-child(3) {
					background: #3a331a;
				}
				[data-theme="dark"] .trading-sales-summary-cards .report-summary .summary-item:nth-child(4) {
					background: #3a1f2b;
				}
			`;
			document.head.appendChild(style);
		}
		report.page.wrapper.addClass("trading-sales-summary-cards");
	},
};
