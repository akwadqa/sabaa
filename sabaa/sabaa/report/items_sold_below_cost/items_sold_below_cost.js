// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.query_reports["Items Sold Below Cost"] = {
	"filters": [
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
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
			get_data: function(txt) {
                return frappe.db.get_link_options("Item Group", txt);
            },
			on_change: function() {
                frappe.query_report.set_filter_value("item_code", []);
                frappe.query_report.refresh();
            }
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "MultiSelectList",
			options: "Item",
			get_data: function(txt) {
				let item_groups = frappe.query_report.get_filter_value("item_group");
                let filters = {};
                if (item_groups && item_groups.length > 0) {
                    filters["item_group"] = ["in", item_groups];
                }
				return frappe.db.get_link_options("Item", txt, filters);
			}
		},
		{
			fieldname: "sales_invoice",
			label: __("Sales Invoice"),
			fieldtype: "Link",
			options: "Sales Invoice",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		}
	]
};
