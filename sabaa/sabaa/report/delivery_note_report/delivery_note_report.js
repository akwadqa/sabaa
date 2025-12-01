frappe.query_reports["Delivery Note Report"] = {
    filters: [
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",
            reqd: 0
        },
        {
            fieldname: "dn_ref",
            label: "Delivery Note",
            fieldtype: "Link",
            options: "Delivery Note",
            reqd: 0
        },
        {
            fieldname: "item",
            label: "Item (Name / Code / Barcode)",
            fieldtype: "Link",
            options: "Item",
            reqd: 0
        },
        {
            fieldname: "driver_name",
            label: "Driver Name",
            fieldtype: "Link",
            options: "Driver",
            reqd: 0
        },
        {
            fieldname: "status",
            label: "DN Status",
            fieldtype: "Select",
            options: "\nDraft\nTo Bill\nClosed\nCompleted",
            reqd: 0
        },
        {
            fieldname: "warehouse",
            label: "Warehouse",
            fieldtype: "Link",
            options: "Warehouse",
            reqd: 0
        },
        {
            fieldname: "posting_date",
            label: "Posting Date",
            fieldtype: "DateRange",
            reqd: 0
        }
    ],

    onload: function (report) {
        const df = report.get_filter('posting_date');

        setTimeout(() => {
            const wrapper = $(df.$wrapper);

            // Prevent duplicate buttons
            if (wrapper.find('.today-btn').length === 0) {
                wrapper.append(`
                    <button class="btn btn-xs btn-default today-btn"
                        style="margin-left: 50px;
                        margin-top: 10px;
                        width: 90px;">
                        Today
                    </button>
                `);

                wrapper.find(".today-btn").on("click", () => {
                    const today = frappe.datetime.get_today();
                    df.set_value([today, today]);
                    report.refresh();
                });
            }
        }, 400);
    }
};
