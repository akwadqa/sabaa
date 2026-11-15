// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commission Rule", {
	onload(frm) {
		frappe.require("/assets/sabaa/js/commission/commission_dialogs.js");
	},

	refresh(frm) {
		render_tier_sentences(frm);
		render_try_amount(frm);
		if (frm.is_new()) return;
		frm.add_custom_button(__("People"), () =>
			sabaa_commission.people_dialog(frm.doc.name, frappe.datetime.month_start(), () => frm.reload_doc())
		);
	},

	tier_method: render_tier_sentences,
});

frappe.ui.form.on("Commission Tier", {
	threshold: (frm) => render_tier_sentences(frm),
	fixed_amount: (frm) => render_tier_sentences(frm),
	excess_percent: (frm) => render_tier_sentences(frm),
	tiers_remove: (frm) => render_tier_sentences(frm),
});

function money(value) {
	return format_number(value || 0, null, value % 1 ? 2 : 0);
}

function render_tier_sentences(frm) {
	const wrapper = frm.fields_dict.tiers.$wrapper;
	wrapper.find(".tier-sentences").remove();
	if (frm.doc.tier_method !== "Tiered" || !(frm.doc.tiers || []).length) return;
	const lines = frm.doc.tiers.map((tier) => {
		const excess = tier.excess_percent ? ` ${__("(+{0}% above)", [tier.excess_percent])}` : "";
		return `<li>${__("From {0} QAR → {1} QAR", [money(tier.threshold), money(tier.fixed_amount)])}${excess}</li>`;
	});
	wrapper.append(`<ul class="tier-sentences text-muted" style="margin-top: 8px">${lines.join("")}</ul>`);
}

function render_try_amount(frm) {
	const wrapper = frm.fields_dict.tiers.$wrapper;
	wrapper.find(".try-amount").remove();
	if (frm.is_new() || frm.doc.tier_method !== "Tiered") return;
	const area = $(`<div class="try-amount" style="margin-top: 12px; max-width: 420px"><div class="field"></div><p class="result"></p></div>`).appendTo(wrapper);
	const control = frappe.ui.form.make_control({
		parent: area.find(".field"),
		df: {
			fieldtype: "Currency",
			label: __("Try an amount"),
			fieldname: "try_amount",
			change: async () => {
				const amount = control.get_value();
				if (!amount) return area.find(".result").text("");
				const headcount = frm.doc.headcount_base || null;
				const { message } = await frappe.call("sabaa.sabaa.commission.api.preview_tier", { rule: frm.doc.name, amount, headcount });
				area.find(".result").text(message.text);
			},
		},
		render_input: true,
	});
}
