// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.query_reports["Item-wise Purchase & Stock Movement"] = {
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
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			reqd: 1,
			on_change: function () {
				const item_code = frappe.query_report.get_filter_value("item_code");
				const uom_filter = frappe.query_report.get_filter("uom");

				if (item_code) {
					frappe.call({
						method: "sabaa.api.item.get_item_uoms",
						args: { item_code: item_code },
						callback: function (r) {
							if (r.message) {
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
			fieldname: "uom",
			label: __("UOM"),
			fieldtype: "Select",
			reqd: 1,
			options: []
		}
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (data && data.supplier === "Total") {
			value = `<b>${value}</b>`;
		}

		if (column.fieldname === "supplier" && data && data.supplier) {
			const from_date = frappe.query_report.get_filter_value("from_date");
			const to_date = frappe.query_report.get_filter_value("to_date");
			const item_code = frappe.query_report.get_filter_value("item_code");

			const filters = {
				supplier: data.supplier_id,
				item_code: item_code,
				from_date: from_date,
				to_date: to_date
			};

			const query_string = frappe.utils.make_query_string(filters);

			return `
				<a href="/app/query-report/Item-wise Purchase Register${query_string}"
				   target="_blank">
					${value}
				</a>
			`;
		}

		return value;
	}
};
