// Copyright (c) 2025, Akwad Programming and contributors
// For license information, please see license.txt

frappe.query_reports["Item Balance (UOM-wise)"] = {
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
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			on_change: function() {
				const item_code = frappe.query_report.get_filter_value("item_code");
				const uom_filter = frappe.query_report.get_filter("uom");

				if(item_code) {
					frappe.call({
						method: "sabaa.api.item.get_item_uoms",
						args: { item_code: item_code },
						callback: function(r) {
							if(r.message) {
								uom_filter.df.options = r.message;
								uom_filter.refresh();
								uom_filter.set_value(r.message[0]);
							}
						}
					});
				} else {
					uom_filter.df.options = [];
					uom_filter.refresh();
				}
			}
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse"
		},
		{
			fieldname: "uom",
			label: __("UOM"),
			fieldtype: "Select",
			options: []
		}
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (value === "Total") {
			value = value.bold();
		}
		return value;
	}
};
