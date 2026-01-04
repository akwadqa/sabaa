import frappe
from frappe import _
from frappe.utils import flt


def _get_uom_cf_from_item(item_doc, target_uom: str) -> float:
    """Return conversion_factor of target_uom from Item UOM table (relative to stock_uom)."""
    target = (target_uom or "").strip().lower()
    for d in (item_doc.get("uoms") or []):
        if (d.uom or "").strip().lower() == target:
            return flt(d.conversion_factor)
    return 0.0


def calculate_total_pallet_qty(doc, method=None):
    """
    For each PO Item row:
      pallets = (CTN qty) / (Item.custom_pallet_loading_qty)
    Where:
      CTN qty = (qty) / (CTN conversion_factor)
      qty =   row.qty * row.conversion_factor

    Saves:
      row.custom_pallet_loading_qty -> pallets (2 decimals)
      doc.custom_total_pallet_qty   -> sum of row pallets (2 decimals)
    """
    total_pallets = 0.0

    for row in (doc.items or []):
        row.custom_pallet_loading_qty = 0

        if not row.item_code or not flt(row.qty):
            continue

        item_doc = frappe.get_cached_doc("Item", row.item_code)

        cartons_per_pallet = flt(item_doc.get("custom_pallet_loading_qty"))
        if cartons_per_pallet <= 0:
            frappe.throw(
                _("Item {0}: Please set <b>custom_pallet_loading_qty</b> (cartons per pallet) in Item master.")
                .format(frappe.get_desk_link("Item", row.item_code))
            )

        qty =  (flt(row.qty) * (flt(row.conversion_factor) or 1))

        ctn_cf = _get_uom_cf_from_item(item_doc, "Ctn")

        if ctn_cf <= 0 and (row.uom or "").strip().lower() == "ctn":
            ctn_cf = flt(row.conversion_factor)

        if ctn_cf <= 0:
            frappe.throw(
                _("Item {0}: Missing UOM conversion for <b>CTN</b> in Item master (UOMs table).")
                .format(frappe.get_desk_link("Item", row.item_code))
            )

        ctn_qty = qty / ctn_cf
        pallets = ctn_qty / cartons_per_pallet

        pallets_2dp = flt(pallets, 2)
        row.custom_pallet_loading_qty = pallets_2dp

        total_pallets += pallets_2dp

    doc.custom_total_pallet_qty = flt(total_pallets, 2)
