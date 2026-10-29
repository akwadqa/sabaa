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

// Above this many rows the server renders the PDF in the background (DEFAULT_BACKGROUND_ROW_THRESHOLD).
const LARGE_REPORT_ROW_COUNT = 1000;

// Same as core frappe.render_pdf, but it shows progress and errors, and large
// reports can come back as {"queued": 1} from sabaa.override.report_pdf.
frappe.render_pdf = function (html, opts = {}) {
    const row_count = (html.match(/<tr[\s>]/gi) || []).length;
    const progress_alert = frappe.show_alert(
        {
            message:
                row_count > LARGE_REPORT_ROW_COUNT
                    ? __(
                          "Generating PDF for {0} rows. Because of the large amount of data, this can take a few minutes. Please keep this page open.",
                          [format_number(row_count, null, 0)]
                      )
                    : __("Generating PDF..."),
            indicator: "blue",
        },
        // Removed when the response arrives; this only bounds a lost request.
        600
    );

    const formData = new FormData();
    formData.append("html", html);
    if (opts.orientation) {
        formData.append("orientation", opts.orientation);
    }
    formData.append("blob", new Blob([], { type: "text/xml" }));

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/method/frappe.utils.print_format.report_to_pdf");
    xhr.setRequestHeader("X-Frappe-CSRF-Token", frappe.csrf_token);
    xhr.responseType = "arraybuffer";

    xhr.onerror = function () {
        progress_alert.remove();
        show_pdf_error(0);
    };

    xhr.onload = function () {
        progress_alert.remove();
        if (this.status !== 200) {
            show_pdf_error(this.status);
            return;
        }

        const content_type = xhr.getResponseHeader("Content-Type") || "";
        if (content_type.includes("application/json")) {
            const response = JSON.parse(new TextDecoder().decode(xhr.response));
            if (response.message?.queued) {
                frappe.show_alert(
                    {
                        message: __(
                            "The report is large. The PDF is being generated; you will be notified when it is ready."
                        ),
                        indicator: "blue",
                    },
                    10
                );
                // Twice the job timeout, so a job that waits behind another one is still followed.
                const deadline = Date.now() + 2 * response.message.timeout * 1000;
                poll_report_pdf_status(response.message.token, deadline);
            }
            return;
        }

        const blob = new Blob([xhr.response], { type: "application/pdf" });
        const object_url = URL.createObjectURL(blob);
        const hidden_a_tag = document.createElement("a");
        document.body.appendChild(hidden_a_tag);
        hidden_a_tag.style = "display: none";
        hidden_a_tag.href = object_url;
        hidden_a_tag.download = opts.report_name || "report.pdf";
        hidden_a_tag.click();
        window.URL.revokeObjectURL(object_url);
    };
    xhr.send(formData);
};

function show_pdf_error(status) {
    const is_timeout = [502, 504].includes(status);
    frappe.msgprint({
        title: __("PDF Not Generated"),
        message: is_timeout
            ? __(
                  "The PDF took too long to generate because the report has too much data. Please apply filters to reduce the data and try again."
              )
            : __("The PDF could not be generated. Please try again or contact your administrator."),
        indicator: "red",
    });
}

const PDF_STATUS_POLL_INTERVAL = 5000;

// Socket.io is not available on this bench, so the queued PDF is polled. Each poll
// reads one small Redis key on the server. The deadline stops the polling when a
// worker dies without setting a status.
function poll_report_pdf_status(token, deadline) {
    if (Date.now() > deadline) {
        return;
    }

    setTimeout(() => {
        frappe.call({
            method: "sabaa.override.report_pdf.get_report_pdf_status",
            type: "GET",
            args: { token },
            callback: ({ message }) => {
                if (message.status === "Queued") {
                    poll_report_pdf_status(token, deadline);
                } else if (message.status === "Ready") {
                    show_report_pdf_ready(message.file_url);
                } else if (message.status === "Failed") {
                    frappe.msgprint({
                        message: __(
                            "The report PDF could not be generated. Please contact your administrator."
                        ),
                        indicator: "red",
                    });
                }
            },
        });
    }, PDF_STATUS_POLL_INTERVAL);
}

function show_report_pdf_ready(file_url) {
    frappe.msgprint({
        title: __("Report PDF"),
        message: `${__("Your report PDF is ready.")} <a href="${encodeURI(
            file_url
        )}" target="_blank">${__("Download")}</a>`,
        indicator: "green",
    });
}
