frappe.query_reports["Custom Delivery Note"] = {
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
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 0
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 0
        }
    ]
};
