frappe.query_reports["Delivery Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: "Company",
			fieldtype: "Link",
			options: "Company",
			reqd: 0
		},
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
			fieldname: "delivery_note",
			label: __("Delivery Note"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				const from_date = frappe.query_report.get_filter_value("from_date");
				const to_date = frappe.query_report.get_filter_value("to_date");

				return frappe.db.get_link_options("Delivery Note", txt, {
					posting_date: ["between", [from_date, to_date]]
				});
			}
		},

		{
			fieldname: "item",
			label: "Item (Name / Code / Barcode)",
			fieldtype: "Link",
			options: "Item",
			reqd: 0
		},
		{
			fieldname: "driver_name",
			label: "Driver Name",
			fieldtype: "Link",
			options: "Driver",
			reqd: 0
		},
		{
			fieldname: "warehouse",
			label: "Warehouse",
			fieldtype: "Link",
			options: "Warehouse",
			reqd: 0
		}
	],
};
