frappe.ui.form.on("Company", {
    setup(frm) {
        frm.set_query("custom_excise_tax_recoverable_account", () => ({
            filters: {
                company: frm.doc.name,
                is_group: 0,
            },
        }));
    },
});
