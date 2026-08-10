(() => {
 
    frappe.ui.form.on("Employee", {
        refresh(frm) {
            if (frm.is_new()) return;

            frm.add_custom_button(__("View Official Papers"), () => {
                frappe.set_route("query-report", "Employee References", {
                    employee: frm.doc.name,
                });
            });
        },
    });
})();
