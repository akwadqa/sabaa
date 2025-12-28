import frappe
from frappe.utils import flt

def calculate_total_pallet_qty(doc, method=None):
    doc.custom_total_pallet_qty = sum(
        flt(row.custom_pallet_loading_qty) for row in (doc.items or [])
    )
