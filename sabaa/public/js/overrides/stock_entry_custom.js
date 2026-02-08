frappe.ui.form.on('Stock Entry', {
    stock_entry_type: function(frm) {
        if (frm.doc.stock_entry_type === 'Sample Issue') {
            frm.doc.items.forEach(function(row) {
                if (!row.expense_account) {
                    frappe.model.set_value(row.doctype, row.name, 'expense_account', '51321 - Samples Expense - STG');
                }
            });
        }
    }
});

frappe.ui.form.on('Stock Entry Detail', {
    item_code: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        if (frm.doc.stock_entry_type === 'Sample Issue') {
            // Delay slightly to let Frappe's standard logic run first
            setTimeout(() => {
                frappe.model.set_value(row.doctype, row.name, 'expense_account', '51321 - Samples Expense - STG');
            }, 50);
        }
    },
    items_add: function(frm, cdt, cdn) {
        console.log("Add Stock Entry")
        let row = frappe.get_doc(cdt, cdn);
        if (frm.doc.stock_entry_type === 'Sample Issue') {
            frappe.model.set_value(row.doctype, row.name, 'expense_account', '51321 - Samples Expense - STG');
        }
    }
});