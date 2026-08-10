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

    const EXCISE_TAX_DESCRIPTION = "Excise Tax Recoverable";
    const item_excise_cache = {};
    const excise_account_cache = {};

    async function get_items_excise_info(item_codes) {
        const missing = item_codes.filter((code) => !(code in item_excise_cache));
        if (missing.length) {
            const r = await frappe.call({
                method: "sabaa.api.excise.get_items_excise_info",
                args: { item_codes: missing },
            });
            Object.assign(item_excise_cache, r.message || {});
        }
        return item_excise_cache;
    }

    async function get_excise_account(company) {
        if (!company) return null;
        if (!(company in excise_account_cache)) {
            const r = await frappe.db.get_value("Company", company, "custom_excise_tax_recoverable_account");
            excise_account_cache[company] = r.message?.custom_excise_tax_recoverable_account || null;
        }
        return excise_account_cache[company];
    }

    async function recalculate_excise(frm) {
        if (frm.doc.docstatus !== 0 || !frm.doc.items || !frm.doc.items.length) return;

        const item_codes = frm.doc.items.map((d) => d.item_code).filter(Boolean);
        if (!item_codes.length) return;

        const [excise_info, excise_account] = await Promise.all([
            get_items_excise_info(item_codes),
            get_excise_account(frm.doc.company),
        ]);

        let total_excise = 0;

        frm.doc.items.forEach((row) => {
            let rate = 0;
            let amount = 0;

            const info = row.item_code && excise_info[row.item_code];
            if (info && info.is_excisable && info.excise_rate) {
                rate = info.excise_rate;
                const base_qty = flt(row.qty) * (flt(row.conversion_factor) || 1);
                amount = flt(base_qty * rate, precision("amount", row));
            }

            row.custom_excise_rate = rate;
            row.custom_excise_amount = amount;
            total_excise += amount;
        });

        total_excise = flt(total_excise, precision("net_total", frm.doc));
        frm.doc.custom_total_excise = total_excise;
        frm.refresh_field("items");

        let tax_row = (frm.doc.taxes || []).find((t) => t.description === EXCISE_TAX_DESCRIPTION);

        if (total_excise > 0 && excise_account) {
            if (!tax_row) {
                tax_row = frm.add_child("taxes", {
                    charge_type: "Actual",
                    description: EXCISE_TAX_DESCRIPTION,
                });
            }
            tax_row.account_head = excise_account;
            tax_row.tax_amount = total_excise;
            frm.refresh_field("taxes");
        } else if (tax_row) {
            frm.doc.taxes = frm.doc.taxes.filter((t) => t !== tax_row);
            frm.refresh_field("taxes");
        }

        frm.cscript.calculate_taxes_and_totals();
    }

    frappe.ui.form.on("Sales Invoice", {
        company(frm) {
            recalculate_excise(frm);
        },
        items_add(frm) {
            recalculate_excise(frm);
        },
        items_remove(frm) {
            recalculate_excise(frm);
        },
    });

    frappe.ui.form.on("Sales Invoice Item", {
        item_code(frm, cdt, cdn) {
            frappe.after_ajax(() => recalculate_excise(frm));
        },
        qty(frm) {
            recalculate_excise(frm);
        },
        conversion_factor(frm) {
            recalculate_excise(frm);
        },
        uom(frm) {
            recalculate_excise(frm);
        },
    });
})();
