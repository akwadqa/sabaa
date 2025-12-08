import frappe

def execute(filters=None):
	filters = filters or {}

	columns = get_columns()
	data = get_data(filters)

	data = group_delivery_note_rows(data)

	# ---- Collect per-UOM totals ----
	uom_totals = {}
	for d in data:
		uom = d.get("uom")
		qty = d.get("qty", 0)

		if not uom:
			continue

		uom_totals[uom] = uom_totals.get(uom, 0) + qty

	# Build breakdown string like: "15 Ctn, 10 Pcs"
	breakdown_str = ", ".join(f"{qty} {uom}" for uom, qty in uom_totals.items())

	# Total sum of all qty
	total_qty = sum(d.get("qty", 0) for d in data)

	# ---- Add TOTAL ROW WITH BREAKDOWN ----
	data.append({
		"dn_ref": "",
		"barcode": "",
		"item_code": "",
		"item_name": f"<b>Total</b>",  # unchanged
		"uom": "",
		"qty": f"{total_qty} ({breakdown_str})",  # breakdown appended here
		"driver_name": "",
	})

	return columns, data



def get_columns():
    return [
        {"label": "Delivery Note", "fieldname": "dn_ref", "fieldtype": "Link", "options": "Delivery Note", "width": 150},
        {"label": "Item Barcode", "fieldname": "barcode", "fieldtype": "Data", "width": 150},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 120},
        {"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "width": 120},
        {"label": "Driver Name", "fieldname": "driver_name", "fieldtype": "Link", "options": "Driver", "width": 180},
    ]


def get_data(filters):
    conditions = []
    params = {}

    # Apply filters
    if filters.get("company"):
        conditions.append("dn.company = %(company)s")
        params["company"] = filters["company"]

    if filters.get("dn_ref"):
        conditions.append("dn.name = %(dn_ref)s")
        params["dn_ref"] = filters["dn_ref"]

    if filters.get("item"):
        conditions.append("(dni.item_code = %(item)s OR dni.barcode = %(item)s OR dni.item_name LIKE %(item_like)s)")
        params["item"] = filters["item"]
        params["item_like"] = f"%{filters['item']}%"

    if filters.get("driver_name"):
        conditions.append("dn.driver = %(driver_name)s")
        params["driver_name"] = filters["driver_name"]

    if filters.get("status"):
        conditions.append("dn.status = %(status)s")
        params["status"] = filters["status"]

    if filters.get("warehouse"):
        conditions.append("dni.warehouse = %(warehouse)s")
        params["warehouse"] = filters["warehouse"]

    if filters.get("posting_date"):
        from_date, to_date = filters.get("posting_date")

        if from_date:
            conditions.append("dn.posting_date >= %(from_date)s")
            params["from_date"] = from_date

        if to_date:
            conditions.append("dn.posting_date <= %(to_date)s")
            params["to_date"] = to_date


    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
        SELECT
            dni.barcode AS barcode,
            dni.item_code AS item_code,
            dni.item_name AS item_name,
            dni.uom AS uom,
            dni.qty AS qty,
            dn.driver_name AS driver_name,
            dn.name AS dn_ref
        FROM `tabDelivery Note` dn
        INNER JOIN `tabDelivery Note Item` dni
            ON dni.parent = dn.name
        {where_clause}
        ORDER BY dni.item_name
    """

    return frappe.db.sql(query, params, as_dict=True)


def group_delivery_note_rows(data):
    grouped = {}
    result = []

    for row in data:
        driver = row.get("driver_name") or ""
        item = row.get("item_code")
        uom = row.get("uom")
        dn_ref = row.get("dn_ref")

        # CASE 1: No driver → group by item + uom only
        if not driver:
            key = f"EMPTY::{item}::{uom}"
            if key not in grouped:
                grouped[key] = {
                    "barcode": row["barcode"],
                    "item_code": item,
                    "item_name": row["item_name"],
                    "uom": uom,
                    "qty": 0,
                    "driver_name": "",
                    "dn_list": set(),
                }
            grouped[key]["qty"] += row["qty"]
            grouped[key]["dn_list"].add(dn_ref)
            continue

        # CASE 2: Driver exists → group by driver + item + uom
        key = f"{driver}::{item}::{uom}"

        if key not in grouped:
            grouped[key] = {
                "barcode": row["barcode"],
                "item_code": item,
                "item_name": row["item_name"],
                "uom": uom,
                "qty": 0,
                "driver_name": driver,
                "dn_list": set(),
            }

        grouped[key]["qty"] += row["qty"]
        grouped[key]["dn_list"].add(dn_ref)

    for k, row in grouped.items():
        dn_refs = list(row["dn_list"])
        dn_ref_value = dn_refs[0] if len(dn_refs) == 1 else ""

        result.append({
            "barcode": row["barcode"],
            "item_code": row["item_code"],
            "item_name": row["item_name"],
            "uom": row["uom"],
            "qty": row["qty"],
            "driver_name": row["driver_name"],
            "dn_ref": dn_ref_value,
        })

    return result





