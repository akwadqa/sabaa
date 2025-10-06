frappe.provide("sabaa");

(function () {
  const INCLUSIVE_COUNTING = true;

  frappe.ui.form.on("Sales Invoice", {
    payment_terms_template: updateDueDate,
    payment_schedule_add: updateDueDate,
    payment_schedule_remove: updateDueDate,
    before_save: updateDueDate,
  });

  function updateDueDate(frm) {
    if (!frm.doc.posting_date || !frm.doc.payment_terms_template) return;

    // Get the base date
    var baseDate = frappe.datetime.str_to_obj(frm.doc.posting_date);
    if (baseDate && baseDate.getDate() !== 1) {
      var nextMonth = new Date(baseDate.getFullYear(), baseDate.getMonth() + 1, 1);
      baseDate = nextMonth;
    }

    // Fetch credit days
    var creditDays = 0;

    // Get credit days from the template
    if (frm.doc.payment_terms_template) {
      var response = frappe.call({
        method: "frappe.client.get",
        args: { doctype: "Payment Terms Template", name: frm.doc.payment_terms_template },
      });

      if (response && response.message) {
        var template = response.message;
        creditDays = template.credit_days || 0;
      }
    }


    // If no credit days found from template, get from the payment schedule
    if (creditDays === 0 && frm.doc.payment_schedule && frm.doc.payment_schedule.length > 0) {
      var names = [];
      for (var i = 0; i < frm.doc.payment_schedule.length; i++) {
        if (frm.doc.payment_schedule[i].payment_term) {
          names.push(frm.doc.payment_schedule[i].payment_term);
        }
      }

      if (names.length > 0) {
        var response = frappe.call({
          method: "frappe.client.get_list",
          args: {
            doctype: "Payment Term",
            filters: { name: ["in", names] },
            fields: ["credit_days"],
            limit_page_length: names.length,
          },
        });

        if (response && response.message) {
          for (var i = 0; i < response.message.length; i++) {
            var termCreditDays = response.message[i].credit_days || 0;
            if (termCreditDays > creditDays) {
              creditDays = termCreditDays;
            }
          }
        }
      }
    }

    // Adjust for inclusive counting
    var daysToAdd = Math.max(0, creditDays - (INCLUSIVE_COUNTING ? 1 : 0));
    var dueDate = frappe.datetime.add_days(frappe.datetime.obj_to_str(baseDate), daysToAdd);

    // Set the due date if it has changed
    if (frm.doc.due_date !== dueDate) {
      frm.set_value("due_date", dueDate);
    }
  }
})();
