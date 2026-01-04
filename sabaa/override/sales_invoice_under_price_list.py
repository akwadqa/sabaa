import frappe
from frappe.utils import flt

def validate_under_price_list_rate(doc, method=None):

    try:
        doc.under_price_list_rate_detected = 0

        if not doc.get("items"):
            return

        for item in doc.items:
            if not item.item_code or item.get("is_free_item"):
                continue

            price_list_rate = flt(item.get("base_price_list_rate"))
            rate = flt(item.get("base_rate"))

            if price_list_rate <= 0:
                continue

            if rate < price_list_rate:
                doc.under_price_list_rate_detected = 1
                break

    except Exception as e:
        frappe.log_error(
            title="Error in validate_under_price_list_rate (Sales Invoice)",
            message=frappe.get_traceback(),
        )
