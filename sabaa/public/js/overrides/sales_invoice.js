(() => {
    // Keep Sales Invoice title in sync with the selected customer's customer_name.
    // - Runs on the `customer` field change, only while the doc is a Draft.
    // - Waits for ERPNext's own customer-loading ajax to finish first (frappe.after_ajax)
    //   so we don't race or interfere with the standard field population.
    // - Runs again on `validate` so the saved value always reflects the latest customer.

    async function sync_title_with_customer(frm) {
        if (frm.doc.docstatus !== 0) return;

        const title_field = frm.meta.title_field || "customer_name";
        const customer = frm.doc.customer;
        const token = `${customer || ""}-${Date.now()}`;
        frm.__title_sync_token = token;

        if (!customer) {
            frm.set_value(title_field, "");
            frm.refresh_header();
            return;
        }

        const r = await frappe.db.get_value("Customer", customer, "customer_name");

        // Bail out if the customer changed again while this request was in flight.
        if (frm.__title_sync_token !== token) return;

        frm.set_value(title_field, r.message?.customer_name || "");
        frm.refresh_header();
    }

    frappe.ui.form.on("Sales Invoice", {
        customer(frm) {
            frappe.after_ajax(() => sync_title_with_customer(frm));
        },

        validate(frm) {
            return sync_title_with_customer(frm);
        },
    });
})();
