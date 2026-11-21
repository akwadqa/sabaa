// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.query_reports["Transaction Summary Report - Daybook"] = {
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
			default: frappe.datetime.month_start(),
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
			fieldname: "transaction_type",
			label: __("Transaction Type Code"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				const types = [
					["SIV", "Sales Invoice"],
					["DN", "Delivery Note"],
					["CRN", "Credit Note (Sales Return)"],
					["PIV", "Purchase"],
					["DRN", "Debit Note (Purchase Return)"],
					["STG-N", "Stock Issue"],
					["STG-P", "Stock Receipt"],
					["EXP", "Expired"],
					["DAM", "Damaged"],
					["GCN", "Repack"],
					["SJ-NP", "Stock Reconciliation"],
					["STK", "Opening Stock"],
				];
				txt = (txt || "").toLowerCase();
				return types
					.filter(([code, label]) => (code + " " + label).toLowerCase().includes(txt))
					.map(([code, label]) => ({ value: code, description: __(label) }));
			},
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: () => ({
				filters: { company: frappe.query_report.get_filter_value("company") },
			}),
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
	],
};
