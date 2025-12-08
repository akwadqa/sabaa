import frappe

def execute(filters=None):
	filters = filters or {}

	columns = get_columns()
	data = get_data(filters)

	# Group rows (item + uom + driver + delivery note)
	data = group_delivery_note_rows(data)

	# ---- Collect per-UOM totals ----
	uom_totals = {}
	for d in data:
		uom = d.get("uom")
		qty = d.get("qty", 0)
		if not uom:
			continue
		uom_totals[uom] = uom_totals.get(uom, 0) + qty

	breakdown_str = ", ".join(f"{qty} {uom}" for uom, qty in uom_totals.items())
	total_qty = sum(d.get("qty", 0) for d in data)

	# ---- Add TOTAL ROW ----
	data.append({
		"dn_ref": "",
		"barcode": "",
		"item_code": "",
		"item_name": "<b>Total</b>",
		"uom": "",
		"qty": total_qty,
		"driver_name": breakdown_str,
	})

	return columns, data


def get_columns():
	return [
		{"label": "Item Barcode", "fieldname": "barcode", "fieldtype": "Data", "width": 150},
		{"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "width": 120},
		{"label": "UOM", "fieldname": "uom", "fieldtype": "Data", "width": 120},
		{"label": "Driver Name", "fieldname": "driver_name", "fieldtype": "Link", "options": "Driver", "width": 180},
	]


def get_data(filters):
	conditions = []
	params = {}

	# Company
	if filters.get("company"):
		conditions.append("dn.company = %(company)s")
		params["company"] = filters["company"]

	# from_date / to_date
	if filters.get("from_date"):
		conditions.append("dn.posting_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("dn.posting_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	# Item
	if filters.get("item"):
		conditions.append("(dni.item_code = %(item)s OR dni.barcode = %(item)s OR dni.item_name LIKE %(item_like)s)")
		params["item"] = filters["item"]
		params["item_like"] = f"%{filters['item']}%"

	# Driver
	if filters.get("driver_name"):
		conditions.append("dn.driver_name = %(driver_name)s")
		params["driver_name"] = filters["driver_name"]

	# Warehouse
	if filters.get("warehouse"):
		conditions.append("dni.warehouse = %(warehouse)s")
		params["warehouse"] = filters["warehouse"]

	# delivery_note
	if filters.get("delivery_note"):
		conditions.append("dn.name IN %(delivery_note)s")
		params["delivery_note"] = tuple(filters.get("delivery_note"))

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

	for row in data:
		driver = row.get("driver_name") or ""
		item = row.get("item_code")
		uom = row.get("uom")
		dn_ref = row.get("dn_ref")

		# Grouping key: driver + item + uom
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

	# Convert grouped dict → list
	result = []
	for row in grouped.values():
		result.append({
			"barcode": row["barcode"],
			"item_code": row["item_code"],
			"item_name": row["item_name"],
			"uom": row["uom"],
			"qty": row["qty"],
			"driver_name": row["driver_name"],
			"dn_ref": "",
		})

	return result
