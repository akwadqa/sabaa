import frappe
from frappe import _
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice as original_make_sales_invoice

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
    try:
        frappe.set_user("Administrator")

        delivery_note = frappe.get_doc("Delivery Note", source_name)
        delivery_note.flags.ignore_permissions = True

        sales_invoice = original_make_sales_invoice(source_name, target_doc)

        sales_invoice.custom_driver = delivery_note.driver
        sales_invoice.custom_driver_name = delivery_note.driver_name

        return sales_invoice

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Custom make_sales_invoice Error")
        frappe.throw(_("Error while creating Sales Invoice. Check logs."))
