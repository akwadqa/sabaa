frappe.ui.get_print_settings = function (
	pdf,
	callback,
	letter_head,
	pick_columns,
	has_filters = false
) {
	var print_settings = locals[":Print Settings"]["Print Settings"];

	var company = frappe.defaults.get_default("company");
	var default_letter_head = "";

	if (locals[":Company"] && locals[":Company"][company]) {
		default_letter_head = locals[":Company"][company]["default_letter_head"] || "";
	}

	var columns = [
		{
			fieldtype: "Select",
			fieldname: "orientation",
			label: __("Orientation"),
			options: [
				{ value: "Landscape", label: __("Landscape") },
				{ value: "Portrait", label: __("Portrait") },
			],
			default: "Landscape",
		},
		{
			fieldtype: "Link",
			fieldname: "report",
			label: __("Report"),
			options: "Print Format",
			get_query: () => ({
				filters: {
					print_format_for: "Report",
					print_format_type: "JS",
					report: frappe.query_report ? frappe.query_report.report_name : "",
					disabled: 0,
				},
			}),
		},
		{
			fieldtype: "Check",
			fieldname: "with_letter_head",
			label: __("With Letter head"),
			default: print_settings.with_letterhead || 1,  // This line makes it checked by default
		},
		{
			fieldtype: "Link",
			fieldname: "letter_head",
			label: __("Letter Head"),
			depends_on: "with_letter_head",
			options: "Letter Head",
			default: letter_head || default_letter_head,
		},
	];

	if (has_filters) {
		columns.push({
			label: __("Include filters"),
			fieldtype: "Check",
			fieldname: "include_filters",
		});
	}

	if (pick_columns) {
		columns.push(
			{
				label: __("Pick Columns"),
				fieldtype: "Check",
				fieldname: "pick_columns",
			},
			{
				label: __("Select Columns"),
				fieldtype: "MultiCheck",
				fieldname: "columns",
				depends_on: "pick_columns",
				columns: 2,
				select_all: true,
				options: pick_columns.map((df) => ({
					label: __(df.label, null, df.parent),
					value: df.fieldname,
				})),
			}
		);
	}

	return frappe.prompt(
		columns,
		function (data) {
			data = $.extend(print_settings, data);
			if (!data.with_letter_head) {
				data.letter_head = null;
			}
			if (data.letter_head) {
				data.letter_head = frappe.boot.letter_heads[print_settings.letter_head];
			}
			callback(data);
		},
		__("Print Settings")
	);
};
