# your_app/override/due_date_patch.py
import frappe
from frappe import _
from frappe.utils import getdate, add_months, date_diff
from frappe.utils.data import get_first_day, formatdate

def _custom_base(posting_date):
    """Your policy: if posting day == 1 -> use posting date; else -> 1st of next month."""
    d = getdate(posting_date)
    return d if d.day == 1 else get_first_day(add_months(d, 1))

def apply_patch():
    """
    Replace erpnext.accounts.party.validate_due_date_with_template with a version
    that uses your base date rule for Sales Invoice. Other doctypes unchanged.
    """
    import erpnext.accounts.party as party

    # prevent double-patching (e.g., multiple imports/worker processes)
    if getattr(party, "_sabaa_due_date_patched", False):
        return
    party._yourapp_due_date_patched = True

    original_fn = party.validate_due_date_with_template

    def patched_validate_due_date_with_template(posting_date, due_date, bill_date, template_name, doctype=None):
        # If not Sales Invoice, keep ERPNext’s default behavior
        if doctype != "Sales Invoice":
            return original_fn(posting_date, due_date, bill_date, template_name, doctype)

        if not template_name:
            return

        # Recompute the "default allowed" due date using YOUR base date
        base = _custom_base(posting_date)
        default_due_date = party.get_due_date_from_template(template_name, base, bill_date)
        if not default_due_date:
            return

        # If the user-set due_date is later than allowed, keep ERPNext's role logic
        if getdate(due_date) > getdate(default_due_date):
            cc_role = frappe.db.get_single_value("Accounts Settings", "credit_controller")
            if cc_role and (cc_role in frappe.get_roles()):
                party_type = "supplier" if doctype == "Purchase Invoice" else "customer"
                frappe.msgprint(
                    _("Note: Due Date exceeds allowed {0} credit days by {1} day(s)").format(
                        party_type, date_diff(due_date, default_due_date)
                    )
                )
            else:
                frappe.throw(
                    _("Due / Reference Date cannot be after {0}").format(formatdate(default_due_date))
                )

    # install the patch
    party._original_validate_due_date_with_template = original_fn
    party.validate_due_date_with_template = patched_validate_due_date_with_template
