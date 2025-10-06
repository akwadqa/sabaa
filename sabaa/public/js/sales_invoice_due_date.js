frappe.provide("sabaa");

(function () {
  // Inclusive counting to match example:
  // 01-May + 30 days => 30-May (not 31-May).
  const INCLUSIVE_COUNTING = true;

  function next_month_first(d) {
    const y = d.getFullYear();
    const m = d.getMonth(); // 0-based
    return new Date(m === 11 ? y + 1 : y, (m + 1) % 12, 1);
  }

  function compute_base_date(posting_date_str) {
    if (!posting_date_str) return null;
    const d = frappe.datetime.str_to_obj(posting_date_str);
    if (!d) return null;
    // Use posting date only if it's exactly the 1st; else jump to 1st of next month
    return d.getDate() === 1 ? d : next_month_first(d);
  }

  // --- Credit days helpers ---
  function credit_days_from_template(template_doc) {
    let cd = 0;
    const terms = (template_doc && template_doc.terms) || [];
    terms.forEach(t => { cd = Math.max(cd, cint(t.credit_days || 0)); });
    return cd;
  }

  function fetch_credit_days_from_template(template_name) {
    if (!template_name) return Promise.resolve(null);
    return frappe.call({
      method: "frappe.client.get",
      args: { doctype: "Payment Terms Template", name: template_name },
    }).then(r => credit_days_from_template(r.message) || null);
  }

  function fetch_credit_days_from_payment_terms(schedule_rows) {
    const names = (schedule_rows || []).map(r => r.payment_term).filter(Boolean);
    if (!names.length) return Promise.resolve(null);

    return frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Payment Term",
        filters: { name: ["in", names] },
        fields: ["name", "credit_days"],
        limit_page_length: names.length,
      },
    }).then(r => {
      let cd = 0;
      (r.message || []).forEach(pt => { cd = Math.max(cd, cint(pt.credit_days || 0)); });
      return cd || null;
    });
  }

  function get_credit_days(frm) {
    // Prefer template; fallback to payment terms referenced in schedule
    return fetch_credit_days_from_template(frm.doc.payment_terms_template)
      .then(cd => (cd !== null ? cd : fetch_credit_days_from_payment_terms(frm.doc.payment_schedule)))
      .then(cd => cd || 0);
  }

  function apply_due_date(frm) {
      if (!frm.doc.posting_date || !frm.doc.payment_terms_template) return;

    const baseObj = compute_base_date(frm.doc.posting_date);
    if (!baseObj) return;

    return get_credit_days(frm).then(credit_days => {
      const baseStr = frappe.datetime.obj_to_str(baseObj);
      const daysToAdd = Math.max(0, (credit_days || 0) - (INCLUSIVE_COUNTING ? 1 : 0));
      const dueStr = frappe.datetime.add_days(baseStr, daysToAdd);

      if (frm.doc.due_date !== dueStr) {
        frm.set_value("due_date", dueStr);
      }
    });
  }

  // Bind to key moments so the UI updates immediately
  frappe.ui.form.on("Sales Invoice", {
    payment_terms_template: apply_due_date,
    payment_schedule_add: apply_due_date,
    payment_schedule_remove: apply_due_date,
    before_save: apply_due_date,
  });
})();
