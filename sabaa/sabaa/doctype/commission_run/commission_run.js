// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commission Run", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Calculate"), () => frm.call("calculate").then(() => frm.reload_doc()));
			if (frm.doc.status === "Calculated") frm.page.set_primary_action(__("Approve"), () => confirm_approval(frm));
			else frm.page.set_primary_action(__("Calculate"), () => frm.call("calculate").then(() => frm.reload_doc()));
		}
		if (frm.doc.status === "Approved") {
			frm.page.set_primary_action(__("Mark Paid"), () => mark_paid(frm));
		}
		if (frm.doc.docstatus === 1) show_live_difference(frm);
	},
});

function confirm_approval(frm) {
	const message = __("Approve {0} QAR for {1} employees? Not assigned: {2} QAR.", [
		format_currency(frm.doc.total_amount),
		frm.doc.employee_count,
		format_currency(frm.doc.not_assigned_amount),
	]);
	frappe.confirm(message, () => frm.savesubmit());
}

function mark_paid(frm) {
	frappe.prompt(
		[{ fieldname: "journal_entry", label: __("Journal Entry"), fieldtype: "Link", options: "Journal Entry" }],
		(values) => frm.call("mark_paid", values).then(() => frm.reload_doc()),
		__("Mark Paid"),
		__("Mark Paid")
	);
}

function show_live_difference(frm) {
	frm.call("get_live_difference").then((r) => {
		if (r.message) {
			frm.dashboard.set_headline(
				__("Changes since approval: {0} QAR", [format_currency(r.message)]),
				"orange"
			);
		}
	});
}
