# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

# Item-wise transaction register: one row per item line of every submitted transaction.
# A Stock Entry line with source and target warehouse gives two rows (STG-N issue, STG-P receipt).

import frappe
from frappe import _

# Voucher type -> (code, code when is_return)
TRADE_CODES = {
	"Sales Invoice": ("SIV", "CRN"),
	"Delivery Note": ("DN", "CRN"),
	"Purchase Receipt": ("PIV", "DRN"),
	"Purchase Invoice": ("PIV", "DRN"),
}
REPACK_PURPOSES = ("Repack", "Manufacture", "Material Consumption for Manufacture")
TRANSFER_CODES = ("STG-N", "STG-P")

# One SELECT per trade voucher type, all with the same column list as the Sales Invoice SELECT.
TRADE_SQL = """
	SELECT '{vt}', p.name, p.posting_date, CAST(p.posting_time AS CHAR), p.creation, i.idx,
		i.item_code, i.item_name, i.qty, i.uom, i.conversion_factor, i.rate, i.warehouse, NULL,
		p.is_return, p.{party}, NULL, NULL, NULL, NULL
	FROM `tab{vt} Item` i INNER JOIN `tab{vt}` p ON p.name = i.parent"""


def execute(filters=None):
	filters = frappe._dict(filters or {})
	codes = get_transaction_codes(filters)
	warehouses = get_warehouses(filters)
	lines = get_lines(filters)
	barcodes = get_barcodes()

	data = []
	for line in lines:
		for row in get_line_rows(line):
			if codes and row["code"] not in codes:
				continue
			if warehouses is not None and row["warehouse"] not in warehouses:
				continue
			data.append(make_row(line, row, barcodes))

	data.sort(key=lambda d: d["sort_key"])
	for d in data:
		d.pop("sort_key", None)

	return get_columns(), data


def get_columns():
	return [
		{"fieldname": "posting_date", "label": _("Transaction Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "transaction_type", "label": _("Transaction Type Code"), "fieldtype": "Data", "width": 100},
		{"fieldname": "voucher_type", "label": _("Voucher Type"), "fieldtype": "Data", "width": 130},
		{"fieldname": "item_code", "label": _("Item Code"), "fieldtype": "Link", "options": "Item", "width": 100},
		{"fieldname": "item_name", "label": _("Item Name"), "fieldtype": "Data", "width": 220},
		{"fieldname": "barcode", "label": _("Item Barcode"), "fieldtype": "Data", "width": 130},
		{"fieldname": "other_entity", "label": _("Other Entity Name"), "fieldtype": "Data", "width": 220},
		{"fieldname": "warehouse", "label": _("Warehouse"), "fieldtype": "Link", "options": "Warehouse", "width": 200},
		{"fieldname": "qty", "label": _("Quantity"), "fieldtype": "Float", "width": 90},
		{"fieldname": "uom", "label": _("UOM"), "fieldtype": "Link", "options": "UOM", "width": 70},
		{"fieldname": "rate", "label": _("Selling Price per unit"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 120},
		{
			"fieldname": "voucher_no",
			"label": _("Common Reference No."),
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 170,
		},
		{"fieldname": "transfer_no", "label": _("Internal Transfer No."), "fieldtype": "Data", "width": 150},
	]


def get_transaction_codes(filters):
	"""The MultiSelectList filter arrives as a list, a JSON list string or a comma-separated string."""
	codes = filters.transaction_type or []
	if isinstance(codes, str):
		codes = frappe.parse_json(codes) if codes.startswith("[") else [c.strip() for c in codes.split(",") if c.strip()]
	return codes


def get_warehouses(filters):
	"""The selected warehouse and all warehouses under it, or None when no warehouse is selected."""
	if not filters.warehouse:
		return None
	wh = frappe.db.get_value("Warehouse", filters.warehouse, ["lft", "rgt"], as_dict=True)
	names = frappe.db.sql_list(
		"SELECT name FROM `tabWarehouse` WHERE lft >= %(lft)s AND rgt <= %(rgt)s",
		{"lft": wh.lft, "rgt": wh.rgt},
	)
	return set(names)


def get_lines(filters):
	values = {"company": filters.company, "from_date": filters.from_date, "to_date": filters.to_date}
	where = " WHERE p.docstatus = 1 AND p.company = %(company)s AND p.posting_date BETWEEN %(from_date)s AND %(to_date)s"
	if filters.item_code:
		where += " AND i.item_code = %(item_code)s"
		values["item_code"] = filters.item_code

	union = (
		"""
	SELECT 'Sales Invoice' AS voucher_type, p.name AS voucher_no, p.posting_date,
		CAST(p.posting_time AS CHAR) AS posting_time, p.creation, i.idx, i.item_code, i.item_name AS line_item_name,
		i.qty, i.uom AS line_uom, i.conversion_factor AS cf, i.rate, i.warehouse AS s_wh, NULL AS t_wh,
		p.is_return, p.customer_name AS party_name,
		NULL AS se_purpose, NULL AS se_type, NULL AS sr_purpose, NULL AS current_qty
	FROM `tabSales Invoice Item` i INNER JOIN `tabSales Invoice` p ON p.name = i.parent"""
		+ where
	)

	for voucher_type, party_field in (
		("Delivery Note", "customer_name"),
		("Purchase Receipt", "supplier_name"),
		("Purchase Invoice", "supplier_name"),
	):
		union += " UNION ALL" + TRADE_SQL.replace("{vt}", voucher_type).replace("{party}", party_field) + where

	union += (
		""" UNION ALL
	SELECT 'Stock Entry', p.name, p.posting_date, CAST(p.posting_time AS CHAR), p.creation, i.idx,
		i.item_code, i.item_name, i.qty, i.uom, i.conversion_factor, i.basic_rate, i.s_warehouse, i.t_warehouse,
		0, NULL, p.purpose, p.stock_entry_type, NULL, NULL
	FROM `tabStock Entry Detail` i INNER JOIN `tabStock Entry` p ON p.name = i.parent"""
		+ where
		+ """
	UNION ALL
	SELECT 'Stock Reconciliation', p.name, p.posting_date, CAST(p.posting_time AS CHAR), p.creation, i.idx,
		i.item_code, i.item_name, i.qty, NULL, 1, i.valuation_rate, i.warehouse, NULL,
		0, NULL, NULL, NULL, p.purpose, i.current_qty
	FROM `tabStock Reconciliation Item` i INNER JOIN `tabStock Reconciliation` p ON p.name = i.parent"""
		+ where
	)

	return frappe.db.sql(
		"SELECT u.*, COALESCE(itm.item_name, u.line_item_name) AS item_name, COALESCE(u.line_uom, itm.stock_uom) AS uom"
		" FROM (" + union + ") u LEFT JOIN `tabItem` itm ON itm.name = u.item_code",
		values,
		as_dict=True,
	)


def get_barcodes():
	"""First barcode of each (item, UOM) pair."""
	barcodes = {}
	for b in frappe.db.sql(
		"SELECT parent, uom, barcode FROM `tabItem Barcode` WHERE parenttype = 'Item' ORDER BY parent, idx",
		as_dict=True,
	):
		barcodes.setdefault((b.parent, b.uom), b.barcode)
	return barcodes


def get_line_rows(line):
	"""Report rows of one item line: each is {code, warehouse, qty, leg, rate}. Leg orders STG-N before STG-P."""
	vt = line.voucher_type
	qty = abs(line.qty or 0)
	rate = line.rate or 0
	rows = []

	if vt in TRADE_CODES:
		code = TRADE_CODES[vt][1] if line.is_return else TRADE_CODES[vt][0]
		rows.append({"code": code, "warehouse": line.s_wh, "qty": qty, "leg": 0})

	elif vt == "Stock Entry":
		rate = rate * (line.cf or 1)  # basic_rate is per stock UOM; show it per line UOM
		if line.se_type in ("Damage", "Expiry"):
			code = "DAM" if line.se_type == "Damage" else "EXP"
			rows.append({"code": code, "warehouse": line.s_wh or line.t_wh, "qty": qty, "leg": 0})
		elif line.se_purpose in REPACK_PURPOSES:
			rows.append({"code": "GCN", "warehouse": line.s_wh or line.t_wh, "qty": qty, "leg": 0 if line.s_wh else 1})
		else:
			if line.s_wh:
				rows.append({"code": "STG-N", "warehouse": line.s_wh, "qty": qty, "leg": 0})
			if line.t_wh:
				rows.append({"code": "STG-P", "warehouse": line.t_wh, "qty": qty, "leg": 1})

	elif vt == "Stock Reconciliation":
		if line.sr_purpose == "Opening Stock":
			rows.append({"code": "STK", "warehouse": line.s_wh, "qty": qty, "leg": 0})
		else:  # signed difference: counted qty - system qty
			diff = round((line.qty or 0) - (line.current_qty or 0), 3)
			rows.append({"code": "SJ-NP", "warehouse": line.s_wh, "qty": diff, "leg": 0})

	for row in rows:
		row["rate"] = rate
	return rows


def make_row(line, row, barcodes):
	is_transfer = row["code"] in TRANSFER_CODES and line.s_wh and line.t_wh
	return {
		"posting_date": line.posting_date,
		"transaction_type": row["code"],
		"voucher_type": line.voucher_type,
		"item_code": line.item_code,
		"item_name": line.item_name,
		"barcode": barcodes.get((line.item_code, line.uom)),
		"other_entity": line.party_name,
		"warehouse": row["warehouse"],
		"qty": row["qty"],
		"uom": line.uom,
		"rate": row["rate"],
		"amount": round(row["qty"] * row["rate"], 2),
		"voucher_no": line.voucher_no,
		"transfer_no": line.voucher_no if is_transfer else None,
		"sort_key": (
			str(line.posting_date),
			line.posting_time or "",
			str(line.creation),
			line.voucher_no,
			line.idx or 0,
			row["leg"],
		),
	}
