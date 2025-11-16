# sabaa/sabaa/overrides/sales_invoice_due_date.py

import frappe
from frappe.utils import getdate, add_days, add_months, get_first_day


def apply_custom_due_date(doc, method=None):
    try:
        # ============================================
        # 1. Posting date required
        # ============================================
        if not doc.posting_date:
            return

        posting = getdate(doc.posting_date)

        # ============================================
        # 2. Calculate base date (always 1st next month)
        # ============================================
        if posting.month == 12:
            next_year = posting.year + 1
            next_month = 1
        else:
            next_year = posting.year
            next_month = posting.month + 1

        base_date = getdate(f"{next_year}-{next_month}-01")

        # ============================================
        # 3. Determine credit days
        # ============================================
        credit_days = 0

        # ---- 3A: FROM TEMPLATE ----
        if doc.payment_terms_template:
            try:
                template = frappe.get_doc("Payment Terms Template", doc.payment_terms_template)

                # Direct credit_days field?
                if hasattr(template, "credit_days") and template.credit_days:
                    credit_days = int(template.credit_days)

                # Child table terms[]
                elif template.terms and hasattr(template.terms[0], "credit_days"):
                    credit_days = int(template.terms[0].credit_days)

            except Exception as e:
                frappe.log_error(f"Error loading Payment Terms Template {doc.payment_terms_template}: {e}",
                                 "Due Date Override (Template Error)")
                # continue without credit days
                credit_days = 0

        # ---- 3B: FALLBACK: PAYMENT TERM rows ----
        if credit_days == 0 and doc.payment_schedule:
            try:
                term_names = [
                    row.payment_term for row in doc.payment_schedule if row.payment_term
                ]

                if term_names:
                    terms = frappe.get_all(
                        "Payment Term",
                        filters={"name": ["in", term_names]},
                        fields=["credit_days"],
                    )

                    credit_days = max(
                        [t.credit_days for t in terms if t.credit_days],
                        default=0
                    )

            except Exception as e:
                frappe.log_error(f"Error reading Payment Terms: {e}",
                                 "Due Date Override (Payment Term Error)")
                credit_days = 0

        # ============================================
        # 4. Inclusive counting (30 = 29)
        # ============================================
        adjusted_days = credit_days - 1 if credit_days > 0 else 0

        # ============================================
        # 5. Calculate final due date
        # ============================================
        final_due_date = add_days(base_date, adjusted_days)

        # ============================================
        # 6. Set main due_date
        # ============================================
        doc.due_date = final_due_date

        # ============================================
        # 7. Update payment_schedule rows
        # ============================================
        if doc.payment_schedule:
            for row in doc.payment_schedule:
                try:
                    row.due_date = final_due_date
                except Exception as e:
                    frappe.log_error(f"Error updating payment schedule row: {e}",
                                     "Due Date Override (Schedule Update Error)")

    except Exception as e:
        frappe.log_error(f"Unexpected error in apply_custom_due_date:\n{frappe.get_traceback()}",
                         "Due Date Override (Fatal Error)")

        frappe.throw("An unexpected error occurred while calculating the Due Date. "
                     "Please contact your system administrator.")
