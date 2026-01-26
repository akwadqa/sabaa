import frappe

def format_quantity_by_uoms(
    total_qty,
    conversions,
    base_uom=None
):
    """
    conversions can be:
    - dict: {"CTN": 24, "BOX": 6, "PCS": 1}
    - list of dicts: [{"uom": "CTN", "conversion_factor": 24}, ...]
    """

    if isinstance(conversions, dict):
        items = conversions.items()
    else:
        items = (
            (row["uom"], row["conversion_factor"])
            for row in conversions
            if row.get("conversion_factor", 0) > 0
        )

    # Sort largest factor first
    sorted_uoms = sorted(items, key=lambda x: x[1], reverse=True)

    remainder = abs(int(total_qty))
    parts = []

    for uom, factor in sorted_uoms:
        qty = remainder // factor
        if qty >= 0:
            parts.append(f"{int(qty)} {uom}")
            remainder %= factor

    if not parts and base_uom:
        return f"0 {base_uom}"

    return " - ".join(parts)

def get_uom_conversion_map(item_code):
    """
    Returns:
    {
        "Pcs": 1,
        "Box": 6,
        "Ctn": 24
    }
    """
    conversions = frappe.db.sql("""
        SELECT uom, conversion_factor
        FROM `tabUOM Conversion Detail`
        WHERE parent = %s
        ORDER BY conversion_factor DESC
    """, item_code, as_dict=True)

    uom_map = {row["uom"]: row["conversion_factor"] for row in conversions}
    return uom_map
