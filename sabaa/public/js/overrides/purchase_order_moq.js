(() => {
    // Simple:
    // - Every time you select an item in PO row -> fetch Item.min_order_qty
    // - If MOQ > 0 -> set row.qty = MOQ
    // - If MOQ missing/0 -> show message with link that opens Item and focuses MOQ field

    // -----------------------------
    // Redirect + focus
    // -----------------------------
    function item_focus_link(item_code) {
        const safe = frappe.utils.escape_html(item_code || "");
        return `<a href="#" class="moq-focus-link" data-item="${safe}">
      ${safe} (set MOQ)
    </a>`;
    }

    // Install click handler once
    if (!window.__moq_focus_link_handler_installed) {
        window.__moq_focus_link_handler_installed = true;

        $(document).on("click", "a.moq-focus-link", function (e) {
            e.preventDefault();

            const item_code = $(this).attr("data-item");
            if (!item_code) return;

            localStorage.setItem("__moq_focus_doctype", "Item");
            localStorage.setItem("__moq_focus_name", item_code);
            localStorage.setItem("__moq_focus_field", "min_order_qty");

            frappe.set_route("Form", "Item", item_code);
        });
    }

    // Focus MOQ field when Item opens
    frappe.ui.form.on("Item", {
        refresh(frm) {
            const dt = localStorage.getItem("__moq_focus_doctype");
            const name = localStorage.getItem("__moq_focus_name");
            const field = localStorage.getItem("__moq_focus_field");

            if (dt !== "Item" || name !== frm.doc.name || field !== "min_order_qty") return;
            if (!frm.fields_dict.min_order_qty) return;

            localStorage.removeItem("__moq_focus_doctype");
            localStorage.removeItem("__moq_focus_name");
            localStorage.removeItem("__moq_focus_field");

            frappe.after_ajax(() => {
                setTimeout(() => {
                    const f = frm.fields_dict.min_order_qty;
                    const $wrapper = f.$wrapper || $(f.wrapper);

                    // If inside tab, show it
                    const $tabPane = $wrapper.closest(".tab-pane");
                    if ($tabPane.length) {
                        const paneId = $tabPane.attr("id");
                        if (paneId) $(`a[href="#${paneId}"]`).tab("show");
                    }

                    try { frm.scroll_to_field("min_order_qty"); } catch (e) { }
                    if (f.$input?.length) f.$input[0].focus();
                }, 300);
            });
        },
    });

    // -----------------------------
    // MOQ logic for PO
    // -----------------------------
    async function set_qty_to_moq_or_warn(cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row || !row.item_code) return;

        const token = `${row.item_code}-${Date.now()}`;
        row.__moq_token = token;

        const r = await frappe.db.get_value("Item", row.item_code, "min_order_qty");
        const moq = flt(r.message?.min_order_qty || 0);

        const latest = locals[cdt][cdn];
        if (!latest || latest.__moq_token !== token) return;

        if (moq > 0) {
            frappe.after_ajax(() => {
                setTimeout(() => {
                    const again = locals[cdt][cdn];
                    if (!again || again.__moq_token !== token) return;

                    frappe.model.set_value(cdt, cdn, "qty", moq);
                }, 50);
            });
        } else {
            frappe.msgprint({
                title: __("MOQ is required"),
                message: __("This item has no MOQ. Please set it in: {0}", [
                    item_focus_link(row.item_code),
                ]),
                indicator: "red",
            });
        }
    }

    frappe.ui.form.on("Purchase Order Item", {
        item_code(frm, cdt, cdn) {
            set_qty_to_moq_or_warn(cdt, cdn);
        },
    });
})();
