// Copyright (c) 2026, Akwad and contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Performance Comparison Report"] = {
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
			fieldname: "finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book",
		},
		{
			fieldname: "filter_based_on",
			label: __("Filter Based On"),
			fieldtype: "Select",
			options: ["Fiscal Year", "Date Range"],
			default: "Fiscal Year",
			reqd: 1,
			on_change: function () {
				let filter_based_on = frappe.query_report.get_filter_value("filter_based_on");
				frappe.query_report.toggle_filter_display(
					"from_fiscal_year",
					filter_based_on === "Date Range"
				);
				frappe.query_report.toggle_filter_display(
					"to_fiscal_year",
					filter_based_on === "Date Range"
				);
				frappe.query_report.toggle_filter_display(
					"period_start_date",
					filter_based_on === "Fiscal Year"
				);
				frappe.query_report.toggle_filter_display(
					"period_end_date",
					filter_based_on === "Fiscal Year"
				);
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "period_start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
			mandatory_depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "period_end_date",
			label: __("End Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
			mandatory_depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "from_fiscal_year",
			label: __("Start Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
		},
		{
			fieldname: "to_fiscal_year",
			label: __("End Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
		},
		{
			fieldname: "comparison_type",
			label: __("Comparison Type"),
			fieldtype: "Select",
			options: ["Year-over-Year", "Previous Period", "Custom"],
			default: "Year-over-Year",
			reqd: 1,
			on_change: function () {
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "comparison_start_date",
			label: __("Comparison Start Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.comparison_type == 'Custom'",
			mandatory_depends_on: "eval:doc.comparison_type == 'Custom'",
		},
		{
			fieldname: "comparison_end_date",
			label: __("Comparison End Date"),
			fieldtype: "Date",
			depends_on: "eval:doc.comparison_type == 'Custom'",
			mandatory_depends_on: "eval:doc.comparison_type == 'Custom'",
		},
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list(),
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
			options: "Cost Center",
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Project", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
			options: "Project",
		},
	],
	tree: true,
	name_field: "account",
	parent_field: "parent_account",
	initial_depth: 3,
	formatter: function (value, row, column, data, default_formatter) {
		if (data && column.fieldname == "account") {
			value = data.account_name || value;
			if (data.account || data.accounts) {
				column.link_onclick =
					"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(data) + ")";
			}
			column.is_tree = true;
		}

		value = default_formatter(value, row, column, data);

		if (data && !data.parent_account) {
			value = $(`<span>${value}</span>`);
			var $value = $(value).css("font-weight", "bold");
			if (data.warn_if_negative && data[column.fieldname] < 0) {
				$value.addClass("text-danger");
			}
			value = $value.wrap("<p></p>").parent().html();
		}

		return value;
	},
	onload: function (report) {
		let fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today());
		var filters = report.get_values();

		if (!filters.period_start_date || !filters.period_end_date) {
			frappe.model.with_doc("Fiscal Year", fiscal_year, function (r) {
				var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
				frappe.query_report.set_filter_value({
					period_start_date: fy.year_start_date,
					period_end_date: fy.year_end_date,
				});
			});
		}
	},
};

// Set default fiscal year values
(function () {
	let fy = erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), false, false);
	if (fy) {
		let filters = frappe.query_reports["Performance Comparison Report"].filters;
		filters.forEach((f) => {
			if (["from_fiscal_year", "to_fiscal_year"].includes(f.fieldname)) {
				f.default = fy;
			}
		});
	}
})();
