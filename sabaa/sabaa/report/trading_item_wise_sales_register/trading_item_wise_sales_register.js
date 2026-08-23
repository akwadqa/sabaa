// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.query_reports["Trading Item-wise Sales Register"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
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
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: function () {
				const company = frappe.query_report.get_filter_value("company");
				return {
					filters: { company: company },
				};
			},
		},
		{
			fieldname: "brand",
			label: __("Brand"),
			fieldtype: "Link",
			options: "Brand",
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "salesperson",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person",
		},
		{
			label: __("Group By"),
			fieldname: "group_by",
			fieldtype: "Select",
			options: ["", "Customer Group", "Customer", "Item Group", "Item", "Territory", "Invoice"],
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) {
			value = value.bold();
		}
		return value;
	},
	// //Fill inline filter with the actual filter values
	// after_datatable_render: function (datatable) {
	// 	const filters = {};

	// 	const customer_group = frappe.query_report.get_filter_value("customer_group");
	// 	if (customer_group) {
	// 		const col_index = datatable.datamanager.getColumnIndexById("customer_group");
	// 		if (col_index > -1) {
	// 			filters[col_index] = customer_group;
	// 		}
	// 	}

	// 	const customers = frappe.query_report.get_filter_value("customer");
	// 	if (customers && customers.length === 1) {
	// 		const col_index = datatable.datamanager.getColumnIndexById("customer_name");
	// 		if (col_index > -1) {
	// 			filters[col_index] = customers[0];
	// 		}
	// 	}

	// 	if (Object.keys(filters).length) {
	// 		datatable.columnmanager.toggleFilter(true);
	// 		datatable.columnmanager.header.querySelectorAll('.dt-filter').forEach((input) => {
	// 			const value = filters[input.dataset.colIndex];
	// 			if (value) input.value = value;
	// 		});
	// 		datatable.columnmanager.applyFilter(filters);
	// 	}
	// },
};
