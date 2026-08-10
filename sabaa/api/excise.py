import frappe


@frappe.whitelist()
def get_items_excise_info(item_codes):
    if isinstance(item_codes, str):
        item_codes = frappe.parse_json(item_codes)

    item_codes = list(set(filter(None, item_codes or [])))
    if not item_codes:
        return {}

    rows = frappe.get_all(
        "Item",
        filters={"name": ["in", item_codes]},
        fields=["name", "custom_is_excisable", "custom_excise_rate"],
    )

    return {
        row.name: {
            "is_excisable": row.custom_is_excisable,
            "excise_rate": row.custom_excise_rate,
        }
        for row in rows
    }
