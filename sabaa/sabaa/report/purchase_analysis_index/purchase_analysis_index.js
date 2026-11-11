// Copyright (c) 2026, Akwad Programming and contributors
// For license information, please see license.txt

frappe.query_reports["Purchase Analysis Index"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
			description: __("Sales are taken for the Sales Months before this date"),
		},
		{
			fieldname: "sales_months",
			label: __("Sales Months"),
			fieldtype: "Int",
			reqd: 1,
			default: 3,
			description: __("1 to 12 months"),
		},
		{
			fieldname: "to_date",
			label: __("Stock As Of"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "uom",
			label: __("UOM"),
			fieldtype: "Link",
			options: "UOM",
			reqd: 1,
			default: "Ctn",
		},
		{
			fieldname: "target_months",
			label: __("Target Cover (Months)"),
			fieldtype: "Float",
			default: 2,
		},
		{
			fieldname: "supplier",
			label: __("Supplier"),
			fieldtype: "Link",
			options: "Supplier",
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "only_to_order",
			label: __("Only Items to Order"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "show_details",
			label: __("Show Details"),
			fieldtype: "Check",
			default: 0,
		},
	],

	onload() {
		frappe.dom.set_style(
			`.report-summary .summary-item.pai-card-filter { cursor: pointer; border-radius: var(--border-radius-md); }
			.report-summary .summary-item.pai-card-filter:hover { background-color: var(--subtle-accent); }
			.report-summary .summary-item.pai-card-active,
			.report-summary .summary-item.pai-card-active:hover {
				background-color: var(--subtle-fg);
				box-shadow: inset 0 0 0 1px var(--gray-400);
			}`,
			"purchase-analysis-index-cards"
		);
	},

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data || !data.item_code) return value;
		const field = column.fieldname;

		if (field === "status") {
			const colors = { Order: "red", OK: "green", Overstock: "orange", "No Sales": "gray" };
			const label = __(data.status);
			return `<span class="indicator-pill ${colors[data.status] || "gray"}">${label}</span>`;
		}
		if (field === "suggested" && data.suggested > 0) {
			return `<b style="color: var(--red-600)">${value}</b>`;
		}
		const is_sales = field.startsWith("sales_") || field === "current_month_sales";
		if (is_sales && data[field] < 0) {
			const title = __("Returns higher than sales");
			return `<span style="color: var(--red-600)" title="${title}">${value}</span>`;
		}
		if (field === "uom" && data.uom_fallback) {
			const title = __("No conversion to the selected UOM, shown in stock UOM");
			const uom = frappe.utils.escape_html(data.uom);
			return `<span style="color: var(--orange-600); font-weight: 600" title="${title}">${uom}</span>`;
		}
		if ((field === "cover" || field === "cover_all") && data.status === "Order") {
			return `<span style="color: var(--red-600)">${value}</span>`;
		}
		if (column.fieldtype === "Link") {
			// A new tab keeps the report, its filters and the selected card open.
			// The Link formatter returns one <a> element, so no HTML parsing is needed.
			return value.replace(/^<a /, '<a target="_blank" rel="noopener" ');
		}
		return value;
	},

	get_datatable_options(options) {
		// Sorting renders every row again, so the card filter must be applied again.
		options.events = {
			...options.events,
			onSortColumn: () => this.active_card && this.apply_card_filter(),
		};
		return options;
	},

	after_datatable_render(datatable) {
		this.datatable = datatable;
		this.active_card = null;
		this.cards = this.bind_summary_cards();

		// A column filter shows rows from all items. Apply the card filter on top of it again,
		// after the datatable's own 300 ms filter debounce.
		const reapply = frappe.utils.debounce(
			() => this.active_card && this.apply_card_filter(),
			400
		);
		$(datatable.header).off("keydown.pai").on("keydown.pai", ".dt-filter", reapply);
	},

	bind_summary_cards() {
		const report = frappe.query_report;
		// "Add Column" renders the datatable again without new cards, so unbind first.
		const $items = report.$summary.find(".summary-item").off(".pai");

		return (report.raw_data.report_summary || [])
			.map((summary, index) => ({ row_filter: summary.row_filter, $el: $items.eq(index) }))
			.filter((card) => card.row_filter)
			.map((card) => {
				card.$el
					.addClass("pai-card-filter")
					.removeClass("pai-card-active")
					.attr({
						role: "button",
						tabindex: 0,
						"aria-pressed": "false",
						title: __("Click to show only these items. Click again to show all."),
					})
					.on("click.pai", () => this.toggle_card(card))
					.on("keydown.pai", (event) => {
						if (event.key === "Enter" || event.key === " ") {
							event.preventDefault();
							this.toggle_card(card);
						}
					});
				return card;
			});
	},

	toggle_card(card) {
		this.active_card = this.active_card === card ? null : card;
		for (const each of this.cards) {
			const is_active = each === this.active_card;
			each.$el
				.toggleClass("pai-card-active", is_active)
				.attr("aria-pressed", String(is_active));
		}
		this.apply_card_filter();
	},

	apply_card_filter() {
		const { datamanager, columnmanager, rowmanager } = this.datatable;
		const column_filters = columnmanager.getAppliedFilters();
		// The datatable filters in a later task. Skip it when there is no column filter
		// (always the case after a sort), so the browser never paints unfiltered rows.
		const filtered = Object.keys(column_filters).length
			? datamanager.filterRows(column_filters).then(({ rowsToShow }) => rowsToShow)
			: Promise.resolve(datamanager.getAllRowIndices());

		filtered.then((indices) => {
			rowmanager.showRows(
				indices.filter((index) => this.matches_card(datamanager.getData(index)))
			);
		});
	},

	matches_card(data) {
		const row_filter = this.active_card?.row_filter || {};
		return Object.entries(row_filter).every(([field, value]) => data[field] === value);
	},
};
