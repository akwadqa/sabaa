// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

const COMMISSION_STATUS_COLORS = {
	Ready: "green",
	"Needs setup": "orange",
	"Missing data": "orange",
	"Waiting for business input": "gray",
	"Not assigned": "red",
};

function commission_quarter_options() {
	const year = new Date().getFullYear();
	const options = [];
	for (const y of [year - 1, year, year + 1]) {
		for (const q of [1, 2, 3, 4]) options.push(`${y}-Q${q}`);
	}
	return options;
}

frappe.query_reports["Sales Commission & Incentive"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "period_type", label: __("Period"), fieldtype: "Select", options: "Month\nQuarter", default: "Month" },
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			depends_on: "eval:doc.period_type == 'Month'",
			on_change() {
				const value = frappe.query_report.get_filter_value("month");
				const first = value && frappe.datetime.month_start(value);
				if (value && first !== value) {
					frappe.query_report.set_filter_value("month", first);
					return;
				}
				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "quarter",
			label: __("Quarter"),
			fieldtype: "Select",
			options: commission_quarter_options().join("\n"),
			depends_on: "eval:doc.period_type == 'Quarter'",
		},
		{ fieldname: "plan", label: __("Plan"), fieldtype: "Link", options: "Commission Plan" },
		{ fieldname: "category", label: __("Category"), fieldtype: "Select", options: "\nTraditional Trade\nModern Trade\nSales Management\nSmile24\nLogistics\nTenders" },
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "view", label: __("View"), fieldtype: "Select", options: "Summary by Employee\nDetail", default: "Summary by Employee" },
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data && data.status) {
			const color = COMMISSION_STATUS_COLORS[data.status] || "gray";
			return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(data.status)}</span>`;
		}
		if (data && !data.employee && column.fieldname === "employee_name") {
			return `<b>${value}</b>`;
		}
		return value;
	},
};
