// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt
// People and Missing-months dialogs, shared by the Commission Setup page and the Commission Rule form.

window.sabaa_commission = window.sabaa_commission || {};
const SC_API = "sabaa.sabaa.commission.api";
const esc = (value) => frappe.utils.escape_html(value == null ? "" : String(value));

sabaa_commission.people_dialog = async function (rule, month, on_saved) {
	const [{ message: people }, doc] = await Promise.all([
		frappe.call(`${SC_API}.get_people`, { rule, month }),
		frappe.db.get_doc("Commission Rule", rule),
	]);
	const uses_percent = (doc.shares || []).some((share) => share.split === "By Assignment %");
	const dialog = new frappe.ui.Dialog({
		title: __("People — {0}", [doc.rule_name]),
		size: "large",
		fields: [
			{ fieldname: "table", fieldtype: "HTML" },
			{ fieldname: "total", fieldtype: "HTML" },
			{ fieldname: "add_section", fieldtype: "Section Break", label: __("Add assistant"), collapsible: 1 },
			{ fieldname: "assistant", label: __("Assistant"), fieldtype: "Link", options: "Employee" },
			{ fieldname: "col", fieldtype: "Column Break" },
			{ fieldname: "salesman", label: __("Works with salesman"), fieldtype: "Link", options: "Sales Person" },
		],
		primary_action_label: __("Save"),
		primary_action: async () => {
			const rows = collect_people(dialog, uses_percent);
			const { assistant, salesman } = dialog.get_values();
			if (assistant && salesman) rows.push({ employee: assistant, assistant_of: salesman });
			await frappe.call(`${SC_API}.save_people`, { rule, month, rows });
			dialog.hide();
			frappe.show_alert({ message: __("Saved"), indicator: "green" });
			on_saved && on_saved();
		},
	});
	render_people(dialog, people, uses_percent);
	dialog.show();
};

function render_people(dialog, people, uses_percent) {
	const header = `<tr><th>${__("Name")}</th><th>${__("Source")}</th><th>${__("Exclude")}</th>${uses_percent ? `<th>${__("Share %")}</th>` : ""}</tr>`;
	const rows = people
		.map(
			(p) => `<tr data-employee="${esc(p.employee)}">
				<td>${esc(p.employee_name)}${p.assistant_of ? ` <span class="text-muted">· ${__("assists {0}", [esc(p.assistant_of)])}</span>` : ""}${p.employee ? "" : ` <span class="text-danger">${__("no employee")}</span>`}</td>
				<td><span class="indicator-pill gray">${esc(__(p.source))}</span></td>
				<td><input type="checkbox" class="exclude" ${p.excluded ? "checked" : ""} ${p.employee ? "" : "disabled"}></td>
				${uses_percent ? `<td><input type="number" class="form-control input-xs percent" style="width: 90px" value="${p.percent ?? ""}"></td>` : ""}
			</tr>`
		)
		.join("");
	const empty = people.length ? "" : `<p class="text-muted">${__("No one is paid by this rule for this month yet.")}</p>`;
	dialog.fields_dict.table.$wrapper.html(`${empty}<table class="table table-sm">${header}${rows}</table>`);
	if (uses_percent) {
		const update = () => update_percent_total(dialog);
		dialog.fields_dict.table.$wrapper.on("input", ".percent", update);
		update();
	}
}

function update_percent_total(dialog) {
	let total = 0;
	dialog.fields_dict.table.$wrapper.find(".percent").each((_, input) => (total += parseFloat(input.value) || 0));
	total = Math.round(total * 100) / 100;
	const ok = total === 100;
	const text = ok ? "100% ✓" : __("{0}%, {1}% missing", [total, Math.round((100 - total) * 100) / 100]);
	dialog.fields_dict.total.$wrapper.html(`<p class="${ok ? "text-success" : "text-warning"}"><b>${text}</b></p>`);
	dialog.get_primary_btn().prop("disabled", !ok);
}

function collect_people(dialog, uses_percent) {
	const rows = [];
	dialog.fields_dict.table.$wrapper.find("tr[data-employee]").each((_, tr) => {
		const employee = tr.dataset.employee;
		if (!employee) return;
		const row = { employee, exclude: $(tr).find(".exclude").is(":checked") ? 1 : 0 };
		const percent = $(tr).find(".percent").val();
		if (uses_percent && percent !== undefined && percent !== "") row.percent = parseFloat(percent);
		rows.push(row);
	});
	return rows;
}

sabaa_commission.missing_figures_dialog = async function (plan, on_saved) {
	if (!plan) return frappe.msgprint(__("Choose a plan first."));
	const { message: grid } = await frappe.call(`${SC_API}.get_missing_figure_grid`, { plan });
	const month_labels = grid.months.map((m) => moment(m).format("MMMM YYYY"));
	const dialog = new frappe.ui.Dialog({
		title: __("Months before ERPNext"),
		size: "extra-large",
		fields: [
			{ fieldname: "help", fieldtype: "HTML", options: `<p class="text-muted">${__("Enter each month's total. Paste from Excel: one row per person, name then one column per month.")}</p>` },
			{ fieldname: "grid", fieldtype: "HTML" },
		],
		primary_action_label: __("Save"),
		primary_action: async () => {
			await frappe.call(`${SC_API}.save_missing_figures`, { plan, rows: collect_figures(dialog) });
			dialog.hide();
			frappe.show_alert({ message: __("Saved"), indicator: "green" });
			on_saved && on_saved();
		},
	});
	const html = grid.rules.length
		? grid.rules.map((rule) => render_figure_rule(rule, grid.months, month_labels)).join("")
		: `<p class="text-muted">${__("No rule in this plan uses a three-month average.")}</p>`;
	dialog.fields_dict.grid.$wrapper.html(html);
	dialog.fields_dict.grid.$wrapper.on("paste", "textarea.paste", (event) => paste_rows(event));
	dialog.show();
};

function render_figure_rule(rule, months, labels) {
	const header = `<tr><th>${__("Sales Person")}</th>${labels.map((l) => `<th>${esc(l)}</th>`).join("")}</tr>`;
	const rows = rule.rows
		.map(
			(row) => `<tr data-rule="${esc(rule.rule)}" data-sales-person="${esc(row.sales_person || "")}" data-label="${esc(row.label)}">
				<td>${esc(row.label)}</td>
				${months.map((m) => `<td><input type="number" class="form-control input-xs" data-month="${m}" value="${row.values[m] ?? ""}"></td>`).join("")}
			</tr>`
		)
		.join("");
	return `<div class="figure-rule" style="margin-bottom: 24px">
		<h5>${esc(rule.rule_name)}</h5>
		<table class="table table-sm">${header}${rows}</table>
		<textarea class="form-control paste" rows="2" placeholder="${__("Paste from Excel here")}"></textarea>
	</div>`;
}

function paste_rows(event) {
	const text = (event.originalEvent.clipboardData || window.clipboardData).getData("text");
	const block = $(event.target).closest(".figure-rule");
	text.split(/\r?\n/).forEach((line) => {
		const [label, ...values] = line.split("\t");
		const tr = block.find("tr[data-label]").filter((_, row) => row.dataset.label.trim().toLowerCase() === (label || "").trim().toLowerCase());
		tr.find("input").each((index, input) => {
			if (values[index] !== undefined) input.value = values[index].replace(/,/g, "").trim();
		});
	});
	event.preventDefault();
}

function collect_figures(dialog) {
	const rows = [];
	dialog.fields_dict.grid.$wrapper.find("tr[data-rule]").each((_, tr) => {
		$(tr).find("input").each((_index, input) => {
			rows.push({ rule: tr.dataset.rule, sales_person: tr.dataset.salesPerson || null, month: input.dataset.month, amount: input.value });
		});
	});
	return rows;
}
