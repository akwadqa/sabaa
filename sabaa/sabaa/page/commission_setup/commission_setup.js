// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

const COMMISSION_API = "sabaa.sabaa.commission.api";
const STATUS_COLORS = { Ready: "green", "Needs setup": "orange", "Waiting for business input": "gray" };

frappe.pages["commission-setup"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Commission Setup"), single_column: true });
	frappe.require("/assets/sabaa/js/commission/commission_dialogs.js", () => {
		wrapper.commission_setup = new CommissionSetup(page);
	});
};

frappe.pages["commission-setup"].on_page_show = function (wrapper) {
	wrapper.commission_setup && wrapper.commission_setup.refresh();
};

class CommissionSetup {
	constructor(page) {
		this.page = page;
		this.body = $('<div class="commission-setup"></div>').appendTo(page.main);
		this.plan = page.add_field({ fieldname: "plan", label: __("Plan"), fieldtype: "Link", options: "Commission Plan", change: () => this.refresh() });
		this.month = page.add_field({ fieldname: "month", label: __("Month"), fieldtype: "Date", default: frappe.datetime.month_start(), change: () => this.refresh() });
		page.set_primary_action(__("Check setup"), () => this.refresh());
		page.add_inner_button(__("Missing months"), () => sabaa_commission.missing_figures_dialog(this.plan.get_value(), () => this.refresh()));
		page.add_inner_button(__("Copy plan to new period"), () => this.copy_plan());
		page.add_inner_button(__("Open report"), () =>
			frappe.set_route("query-report", "Sales Commission & Incentive", { plan: this.plan.get_value(), month: this.month.get_value() })
		);
		this.set_default_plan();
	}

	async set_default_plan() {
		const plans = await frappe.db.get_list("Commission Plan", { fields: ["name"], order_by: "valid_from desc", limit: 1 });
		if (plans.length) this.plan.set_value(plans[0].name);
		else this.render_empty();
	}

	async refresh() {
		const plan = this.plan.get_value();
		if (!plan) return this.render_empty();
		const month = frappe.datetime.month_start(this.month.get_value() || frappe.datetime.get_today());
		const { message: rows } = await frappe.call(`${COMMISSION_API}.get_setup_status`, { plan, month });
		this.render(rows, month);
	}

	render_empty() {
		this.body.html(`<div class="empty"><p>${__("No commission plan yet.")}</p></div>`);
		$(`<button class="btn btn-primary">${__("Create default plan")}</button>`)
			.appendTo(this.body.find(".empty"))
			.on("click", async () => {
				const { message } = await frappe.call(`${COMMISSION_API}.create_default_plan`);
				this.plan.set_value(message);
			});
	}

	render(rows, month) {
		this.body.empty();
		const groups = {};
		rows.forEach((row) => (groups[row.category || __("Settings")] ||= []).push(row));
		Object.entries(groups).forEach(([category, rules]) => {
			const section = $(`<div class="category"><h4>${frappe.utils.escape_html(category)}</h4></div>`).appendTo(this.body);
			rules.forEach((rule) => section.append(this.render_rule(rule, month)));
		});
	}

	render_rule(rule, month) {
		const color = STATUS_COLORS[rule.status] || "gray";
		const row = $(`<div class="rule">
			<div class="rule-head">
				<span class="rule-name">${frappe.utils.escape_html(rule.rule_name)}</span>
				<span class="indicator-pill ${color}">${__(rule.status)}</span>
			</div>
			<div class="rule-summary">${frappe.utils.escape_html(rule.summary || "")}</div>
		</div>`);
		if (rule.name) row.find(".rule-name").css("cursor", "pointer").on("click", () => frappe.set_route("Form", "Commission Rule", rule.name));
		rule.problems.forEach((problem) => {
			const line = $(`<div class="problem">${frappe.utils.escape_html(problem.message)} → <a>${__("Fix")}</a></div>`);
			line.find("a").on("click", () => this.fix(problem, month));
			row.append(line);
		});
		return row;
	}

	fix(problem, month) {
		const fix = problem.fix || {};
		if (fix.doctype) return frappe.set_route("Form", fix.doctype, fix.name);
		if (fix.action === "people") return sabaa_commission.people_dialog(fix.rule, month, () => this.refresh());
		if (fix.action === "manual_figures") return sabaa_commission.missing_figures_dialog(this.plan.get_value(), () => this.refresh());
	}

	copy_plan() {
		const dialog = new frappe.ui.Dialog({
			title: __("Copy plan to new period"),
			fields: [
				{ fieldname: "new_name", label: __("New plan name"), fieldtype: "Data", reqd: 1 },
				{ fieldname: "valid_from", label: __("From"), fieldtype: "Date", reqd: 1 },
				{ fieldname: "valid_to", label: __("To"), fieldtype: "Date" },
			],
			primary_action_label: __("Copy"),
			primary_action: async (values) => {
				const { message } = await frappe.call(`${COMMISSION_API}.copy_plan`, { plan: this.plan.get_value(), ...values });
				dialog.hide();
				this.plan.set_value(message);
			},
		});
		dialog.show();
	}
}
