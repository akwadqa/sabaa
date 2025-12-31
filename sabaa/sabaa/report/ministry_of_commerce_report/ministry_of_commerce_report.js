frappe.query_reports["Ministry Of Commerce Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today(),
        },
    ],

    onload: function (report) {
        report.page.set_title(__("Ministry Of Commerce Report"));

        if (!document.getElementById("moci-report-style")) {
            const style = document.createElement("style");
            style.id = "moci-report-style";
            style.innerHTML = `
        .page-title .title-text{
          font-size:20px !important;
          font-weight:700 !important;
          letter-spacing:.2px;
        }
        .datatable .dt-header .dt-cell__content{
          font-weight:700 !important;
          font-size:13px !important;
        }
        .datatable .dt-cell__content{
          font-size:13px !important;
        }
        .datatable .dt-row{ height:38px; }
        .moci-ton-cell{ font-variant-numeric: tabular-nums; }
      `;
            document.head.appendChild(style);
        }
    },

    formatter: function (value, row, column, data, default_formatter) {
        const rendered = default_formatter(value, row, column, data);

        if (column.fieldname === "moci_category") {
            return `<span style="font-weight:600;">${rendered}</span>`;
        }

        if (column.fieldname === "total_qty") {
            // Use the already-formatted value to avoid JS errors
            return `
        <div class="text-end moci-ton-cell" style="font-weight:600;">
          ${rendered}
        </div>
      `;
        }

        return rendered;
    },

    get_datatable_options: function (options) {
        return Object.assign(options, { cellHeight: 38 });
    },
};
