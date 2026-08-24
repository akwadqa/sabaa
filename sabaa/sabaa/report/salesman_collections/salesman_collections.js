// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt


frappe.query_reports["Salesman Collections"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: "Saba Trading Group",
			required: 1,
			width: "80",
		},
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
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
			get_data: function(txt) {
                return frappe.db.get_link_options("Customer Group", txt);
            },
			on_change: function() {
                frappe.query_report.set_filter_value("customer", []);
                frappe.query_report.refresh();
            }
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "MultiSelectList",
			options: "Customer",
			get_data: function(txt) {
                let customer_groups = frappe.query_report.get_filter_value("customer_group");
				let filters = {};
                if (customer_groups && customer_groups.length > 0) {
                    filters["customer_group"] = ["in", customer_groups];
                }
				return frappe.db.get_link_options("Customer", txt, filters);
            }
		},
		{
			fieldname: "salesperson",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person"
		},
		{
			fieldname: "group_by_customer_group",
			label: __("Group By Customer Group"),
			fieldtype: "Check"
		},
		{
			fieldname: "group_by_sales_provider",
			label: __("Group By Sales Provider"),
			fieldtype: "Check"
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		if ((data && (data.bold && value === 0)) || value === "" ) {
				value = ""
		}
		else { 
			value = default_formatter(value, row, column, data);
		}
		
		if (data && data.bold) {
			value = value.bold();
		}


		return value;
	}
};
