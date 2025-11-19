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
            label: "DN Ref",
            fieldtype: "Link",
            options: "Delivery Note",
            reqd: 0
        },
        {
            fieldname: "item",
            label: "Item (Name / Code / Barcode)",
            fieldtype: "Data",
            reqd: 0
        },
        {
            fieldname: "driver_name",
            label: "Driver Name",
            fieldtype: "Data",
            reqd: 0
        },
        {
            fieldname: "status",
            label: "DN Status",
            fieldtype: "Select",
            options: "\nDraft\nSubmitted\nCancelled",
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
            fieldname: "group_by_item",
            label: "Group by Item Name",
            fieldtype: "Check",
            default: 0
        }
    ]
};
