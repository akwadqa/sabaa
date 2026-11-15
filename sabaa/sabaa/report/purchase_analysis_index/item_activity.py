# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

"""Per-item stock, sales, purchase and open order figures for the Purchase Analysis Index."""

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import escape_html

if TYPE_CHECKING:
	from sabaa.sabaa.report.purchase_analysis_index.purchase_analysis_index import PurchaseAnalysisIndex

IS_SALE = "sle.voucher_type in ('Sales Invoice', 'Delivery Note')"
IS_PURCHASE = "sle.voucher_type in ('Purchase Receipt', 'Purchase Invoice')"

# Items the supplier ever delivered, invoiced with stock, or was ordered from.
SUPPLIER_ITEMS = """i.name in (
	select pri.item_code from `tabPurchase Receipt Item` pri join `tabPurchase Receipt` pr on pr.name = pri.parent
	where pr.docstatus = 1 and pr.supplier = %(supplier)s
	union
	select pii.item_code from `tabPurchase Invoice Item` pii join `tabPurchase Invoice` pi on pi.name = pii.parent
	where pi.docstatus = 1 and pi.update_stock = 1 and pi.supplier = %(supplier)s
	union
	select poi.item_code from `tabPurchase Order Item` poi join `tabPurchase Order` po on po.name = poi.parent
	where po.docstatus = 1 and po.supplier = %(supplier)s)"""

# Receipt rows up to the Stock As Of date, from Purchase Receipts and stock-updating Purchase Invoices.
RECEIPT_ROWS = """
	select pri.item_code, pr.supplier, pr.posting_date, pr.posting_time, pri.parent, pri.stock_qty, pri.valuation_rate
	from `tabPurchase Receipt Item` pri join `tabPurchase Receipt` pr on pr.name = pri.parent
	where pr.docstatus = 1 and pr.is_return = 0 and pr.posting_date <= %(to_date)s
	union all
	select pii.item_code, pi.supplier, pi.posting_date, pi.posting_time, pii.parent, pii.stock_qty, pii.valuation_rate
	from `tabPurchase Invoice Item` pii join `tabPurchase Invoice` pi on pi.name = pii.parent
	where pi.docstatus = 1 and pi.is_return = 0 and pi.update_stock = 1 and pi.posting_date <= %(to_date)s"""


class ItemActivity:
	"""Load every source the report needs, keyed by item code. Quantities are in stock UOM."""

	def __init__(self, report: "PurchaseAnalysisIndex"):
		self.report = report
		self.params = self.get_params()
		self.warehouse_condition, self.order_warehouse_condition = self.get_warehouse_conditions()

		self.items = self.get_items()
		self.movements = self.get_stock_movements()
		self.purchases = self.get_period_purchases()
		self.last_receipts = self.get_last_receipts()
		self.supplier_lists = self.get_supplier_lists() if report.show_details else {}
		self.open_orders = self.get_open_orders()

	def get_params(self) -> dict:
		report = self.report
		filters = report.filters
		params = {
			"from_date": report.from_date,
			"to_date": report.to_date,
			"uom": report.uom,
			"current_month_start": report.current_month_start,
			"item_code": filters.item_code,
			"supplier": filters.supplier,
		}
		for number, bucket in enumerate(report.window.buckets, start=1):
			params[f"sales_{number}_start"] = bucket.start
			params[f"sales_{number}_end"] = bucket.end

		if filters.warehouse:
			params.update(get_tree_bounds("Warehouse", filters.warehouse, "warehouse"))
		if filters.item_group:
			params.update(get_tree_bounds("Item Group", filters.item_group, "item_group"))
		for group in report.warehouse_groups:
			params.update(get_tree_bounds("Warehouse", group.warehouse, group.fieldname))
		return params

	def get_warehouse_conditions(self) -> tuple[str, str]:
		if not self.report.filters.warehouse:
			return "", ""

		in_tree = "w.lft >= %(warehouse_lft)s and w.rgt <= %(warehouse_rgt)s"
		order_condition = (
			f" and exists (select 1 from `tabWarehouse` w where w.name = poi.warehouse and {in_tree})"
		)
		return f" and {in_tree}", order_condition

	def get_items(self) -> list[dict]:
		items = frappe.db.sql(
			f"""
			select i.name as item_code, i.item_name, i.item_group, i.stock_uom,
				ifnull(i.safety_stock, 0) as safety_stock,
				(select max(c.conversion_factor) from `tabUOM Conversion Detail` c
					where c.parent = i.name and c.parenttype = 'Item' and c.uom = %(uom)s
						and c.conversion_factor > 0) as cf
			from `tabItem` i
			join `tabItem Group` ig on ig.name = i.item_group
			where i.is_stock_item = 1 {self.get_item_conditions()}""",
			self.params,
			as_dict=True,
		)
		settings = self.report.settings
		return [item for item in items if not settings.is_promotional(item.item_name, item.stock_uom)]

	def get_item_conditions(self) -> str:
		filters = self.report.filters
		conditions = []
		if filters.item_group:
			conditions.append("ig.lft >= %(item_group_lft)s and ig.rgt <= %(item_group_rgt)s")
		if filters.item_code:
			conditions.append("i.name = %(item_code)s")
		if filters.supplier:
			conditions.append(SUPPLIER_ITEMS)
		return "".join(f" and {condition}" for condition in conditions)

	def get_stock_movements(self) -> dict:
		"""Monthly sales, period movement and stock as of the Stock As Of date."""
		sales_columns = "".join(
			f"sum(case when sle.posting_date between %(sales_{number}_start)s and %(sales_{number}_end)s"
			f" and {IS_SALE} then -sle.actual_qty else 0 end) as sales_{number},"
			for number in range(1, len(self.report.window.buckets) + 1)
		)
		rows = frappe.db.sql(
			f"""
			select sle.item_code, {sales_columns}
				sum(case when sle.posting_date >= %(current_month_start)s and {IS_SALE}
					then -sle.actual_qty else 0 end) as current_month_sales,
				sum(case when sle.posting_date < %(from_date)s then sle.actual_qty else 0 end) as opening,
				sum(case when sle.posting_date >= %(from_date)s then sle.actual_qty else 0 end) as period_qty,
				sum(case when sle.posting_date >= %(from_date)s and {IS_PURCHASE}
					then sle.actual_qty else 0 end) as purchased_all,
				sum(case when sle.posting_date >= %(from_date)s and {IS_SALE}
					then -sle.actual_qty else 0 end) as sold,
				sum(sle.actual_qty) as closing,
				sum(sle.stock_value_difference) as closing_value
				{self.get_warehouse_group_columns()}
			from `tabStock Ledger Entry` sle
			join `tabWarehouse` w on w.name = sle.warehouse
			where sle.is_cancelled = 0 and sle.posting_date <= %(to_date)s {self.warehouse_condition}
			group by sle.item_code""",
			self.params,
			as_dict=True,
		)
		return {row.item_code: row for row in rows}

	def get_warehouse_group_columns(self) -> str:
		return "".join(
			f", sum(case when w.lft >= %({group.fieldname}_lft)s and w.rgt <= %({group.fieldname}_rgt)s"
			f" then sle.actual_qty else 0 end) as {group.fieldname}"
			for group in self.report.warehouse_groups
		)

	def get_period_purchases(self) -> dict:
		"""Received qty and landed cost between From Date and Stock As Of."""
		supplier_condition = ""
		if self.report.filters.supplier:
			supplier_condition = " and coalesce(pr.supplier, pi.supplier) = %(supplier)s"

		rows = frappe.db.sql(
			f"""
			select sle.item_code, sum(sle.actual_qty) as qty, sum(sle.stock_value_difference) as value
			from `tabStock Ledger Entry` sle
			join `tabWarehouse` w on w.name = sle.warehouse
			left join `tabPurchase Receipt` pr on sle.voucher_type = 'Purchase Receipt' and pr.name = sle.voucher_no
			left join `tabPurchase Invoice` pi on sle.voucher_type = 'Purchase Invoice' and pi.name = sle.voucher_no
			where sle.is_cancelled = 0 and {IS_PURCHASE}
				and sle.posting_date between %(from_date)s and %(to_date)s
				{self.warehouse_condition}{supplier_condition}
			group by sle.item_code""",
			self.params,
			as_dict=True,
		)
		return {row.item_code: row for row in rows}

	def get_last_receipts(self) -> dict:
		"""The latest receipt of each item, with all its rows summed (paid and free qty)."""
		rows = frappe.db.sql(
			f"""
			select item_code, supplier, posting_date, stock_qty, valuation_rate from (
				select receipt.*, row_number() over (partition by receipt.item_code
					order by receipt.posting_date desc, receipt.posting_time desc, receipt.parent desc) as rn
				from (
					select r.item_code, r.supplier, r.posting_date, r.posting_time, r.parent,
						sum(r.stock_qty) as stock_qty,
						sum(r.stock_qty * r.valuation_rate) / nullif(sum(r.stock_qty), 0) as valuation_rate
					from ({RECEIPT_ROWS}) r
					group by r.item_code, r.parent, r.supplier, r.posting_date, r.posting_time
				) receipt
			) latest
			where latest.rn = 1""",
			self.params,
			as_dict=True,
		)
		return {row.item_code: row for row in rows}

	def get_supplier_lists(self) -> dict:
		rows = frappe.db.sql(
			f"""
			select item_code, count(distinct supplier) as count,
				group_concat(distinct supplier order by supplier separator ', ') as names
			from ({RECEIPT_ROWS}) r
			group by item_code""",
			self.params,
			as_dict=True,
		)
		return {row.item_code: row for row in rows}

	def get_open_orders(self) -> dict:
		"""Qty still to receive on submitted, open Purchase Orders."""
		rows = frappe.db.sql(
			f"""
			select poi.item_code, sum((poi.qty - poi.received_qty) * poi.conversion_factor) as pending,
				min(poi.schedule_date) as eta, count(distinct po.name) as po_count
			from `tabPurchase Order Item` poi join `tabPurchase Order` po on po.name = poi.parent
			where po.docstatus = 1 and po.status not in ('Closed', 'Completed', 'On Hold')
				and poi.qty > poi.received_qty {self.order_warehouse_condition}
			group by poi.item_code""",
			self.params,
			as_dict=True,
		)
		return {row.item_code: row for row in rows}


def get_tree_bounds(doctype: str, name: str, prefix: str) -> dict:
	bounds = frappe.db.get_value(doctype, name, ["lft", "rgt"], as_dict=True)
	if not bounds:
		frappe.throw(_("{0} {1} does not exist").format(_(doctype), escape_html(name)))
	return {f"{prefix}_lft": bounds.lft, f"{prefix}_rgt": bounds.rgt}
