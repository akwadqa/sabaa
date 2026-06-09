import frappe


def backfill_dn_details():
    si_items = frappe.db.sql("""
        SELECT
            sii.name,
            sii.parent,
            sii.item_code,
            sii.qty,
            sii.delivery_note
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        WHERE sii.delivery_note IS NOT NULL
          AND sii.delivery_note != ''
          AND (sii.dn_detail IS NULL OR sii.dn_detail = '')
          AND si.docstatus = 1
    """, as_dict=True)

    frappe.log_error(
        title="DN Backfill Started",
        message=f"Found {len(si_items)} SI items to process"
    )

    affected_dns = set()
    fixed_count = 0

    for sii in si_items:
        try:
            dn_items = frappe.db.sql("""
                SELECT name
                FROM `tabDelivery Note Item`
                WHERE parent=%s
                  AND item_code=%s
                  AND qty=%s
            """,
            (
                sii.delivery_note,
                sii.item_code,
                sii.qty,
            ),
            as_dict=True)

            if not dn_items:
                frappe.log_error(
                    title="DN Backfill - No Match",
                    message=f"""
                    SI Item      : {sii.name}
                    Sales Invoice: {sii.parent}
                    Delivery Note: {sii.delivery_note}
                    Item Code    : {sii.item_code}
                    Qty          : {sii.qty}

                    No matching Delivery Note Item found.
                    """
                )
                continue

            if len(dn_items) > 1:
                frappe.log_error(
                    title="DN Backfill - Multiple Matches",
                    message=f"""
                    SI Item      : {sii.name}
                    Sales Invoice: {sii.parent}
                    Delivery Note: {sii.delivery_note}
                    Item Code    : {sii.item_code}
                    Qty          : {sii.qty}

                    Matches:
                    {[d.name for d in dn_items]}
                    """
                )

            dn_detail = dn_items[0].name

            frappe.db.set_value(
                "Sales Invoice Item",
                sii.name,
                "dn_detail",
                dn_detail,
                update_modified=False,
            )

            fixed_count += 1
            affected_dns.add(sii.delivery_note)

        except Exception:
            frappe.log_error(
                title=f"DN Backfill Exception - SI Item {sii.name}",
                message=frappe.get_traceback()
            )

    frappe.db.commit()

    frappe.log_error(
        title="DN Backfill Completed",
        message=f"""
        Fixed SI Items : {fixed_count}
        Affected DNs   : {len(affected_dns)}
        """
    )

    # Update billing status
    for dn_name in affected_dns:
        try:
            si_names = list(set(
                frappe.db.get_all(
                    "Sales Invoice Item",
                    filters={
                        "delivery_note": dn_name,
                        "docstatus": 1,
                    },
                    pluck="parent",
                )
            ))

            for si_name in si_names:
                try:
                    si = frappe.get_doc("Sales Invoice", si_name)
                    si.update_billing_status_in_dn()

                except Exception:
                    frappe.log_error(
                        title=f"Billing Status Update Failed - {si_name}",
                        message=frappe.get_traceback()
                    )

            frappe.db.commit()

        except Exception:
            frappe.log_error(
                title=f"DN Processing Failed - {dn_name}",
                message=frappe.get_traceback()
            )

    remaining = frappe.db.sql("""
        SELECT COUNT(*)
        FROM `tabSales Invoice Item`
        WHERE delivery_note != ''
          AND (dn_detail IS NULL OR dn_detail = '')
    """)[0][0]

    frappe.log_error(
        title="DN Backfill Finished",
        message=f"Remaining SI Items without dn_detail = {remaining}"
    )