import frappe

def execute(filters=None):
    filters = filters or {}

    columns = get_columns()
    data = get_data(filters)

    # Always group by driver now
    data = group_by_driver(data)

    return columns, data



def get_columns():
    return [
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

    # Build conditions SQL
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
        SELECT
            dni.barcode AS barcode,
            dni.item_code AS item_code,
            dni.item_name AS item_name,
            dni.uom AS uom,
            dni.qty AS qty,
            dn.driver_name AS driver_name
        FROM `tabDelivery Note` dn
        INNER JOIN `tabDelivery Note Item` dni
            ON dni.parent = dn.name
        {where_clause}
        ORDER BY dni.item_name
    """

    return frappe.db.sql(query, params, as_dict=True)


def group_by_driver(data):
    grouped = {}
    result = []

    for row in data:
        driver = row.get("driver_name") or ""
        item = row.get("item_code")

        # ===========================
        # CASE 1: Driver is empty
        # → Group by item_code only
        # ===========================
        if not driver:
            key = f"EMPTY::{item}"

            if key not in grouped:
                grouped[key] = {
                    "barcode": row["barcode"],
                    "item_code": item,
                    "item_name": row["item_name"],
                    "uom": row["uom"],
                    "qty": 0,
                    "driver_name": "",
                }

            grouped[key]["qty"] += row["qty"]
            continue

        # ===========================
        # CASE 2: Driver is NOT empty
        # → Group by driver + item_code
        # ===========================
        key = f"{driver}::{item}"

        if key not in grouped:
            grouped[key] = {
                "barcode": row["barcode"],
                "item_code": item,
                "item_name": row["item_name"],
                "uom": row["uom"],
                "qty": 0,
                "driver_name": driver,
            }

        grouped[key]["qty"] += row["qty"]

    # Build final list
    result.extend(grouped.values())

    return result




