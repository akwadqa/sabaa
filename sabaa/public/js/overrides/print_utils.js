frappe.ui.get_print_settings = function (
    pdf,
    callback,
    letter_head,
    pick_columns,
    has_filters = false
) {
    const print_settings = locals[":Print Settings"]["Print Settings"] || {};
    const company = frappe.defaults.get_default("company");

    let default_letter_head = "";

    if (locals[":Company"] && locals[":Company"][company]) {
        default_letter_head =
            locals[":Company"][company]["default_letter_head"] || "";
    }

    const columns = [
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
            fieldname: "print_format",
            options: "Print Format",
            get_query: () => ({
                filters: {
                    print_format_for: "Report",
                    print_format_type: "JS",
                    report: frappe.query_report
                        ? frappe.query_report.report_name
                        : "",
                    disabled: 0,
                },
            }),
        },
        {
            fieldtype: "Check",
            fieldname: "with_letter_head",
            label: __("With Letter Head"),
            default:
                print_settings.with_letterhead ?? 1,
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
            label: __("Include Filters"),
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
                depends_on: "eval: !doc.print_format", 
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
        function (user_settings) {

            const settings = $.extend(
                {},
                print_settings,
                user_settings
            );

            if (!settings.with_letter_head) {
                settings.letter_head = null;
            } else if (settings.letter_head) {
                settings.letter_head =
                    frappe.boot.letter_heads[settings.letter_head];
            }

            if (settings.print_format) {
                settings.pick_columns = 0;
                settings.columns = [];
            }

            callback(settings);
        },
        __("Print Settings")
    );
};
