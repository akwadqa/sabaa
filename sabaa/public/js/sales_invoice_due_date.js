frappe.ui.form.on("Sales Invoice", {
  payment_terms_template: updateDueDateUI,
  posting_date: updateDueDateUI,
});

function updateDueDateUI(frm) {
  if (!frm.doc.posting_date || !frm.doc.payment_terms_template) return;

  let posting = frappe.datetime.str_to_obj(frm.doc.posting_date);

  let baseDate = new Date(posting.getFullYear(), posting.getMonth() + 1, 1);

  frappe.call({
    method: "frappe.client.get",
    args: {
      doctype: "Payment Terms Template",
      name: frm.doc.payment_terms_template
    }
  }).then(res => {
    let creditDays = 0;

    if (res.message && res.message.credit_days) {
      creditDays = res.message.credit_days;
    }

    if (
      creditDays === 0 &&
      res.message &&
      res.message.terms &&
      res.message.terms.length > 0 &&
      res.message.terms[0].credit_days
    ) {
      creditDays = res.message.terms[0].credit_days;
    }

    const INCLUSIVE_COUNTING = true;
    let days = Math.max(0, creditDays - (INCLUSIVE_COUNTING ? 1 : 0));

    let baseDateString =
      `${baseDate.getFullYear()}-${String(baseDate.getMonth() + 1).padStart(2, "0")}-01`;

    let dueDate = frappe.datetime.add_days(baseDateString, days);

    frm.set_value("due_date", dueDate);
  });
}
