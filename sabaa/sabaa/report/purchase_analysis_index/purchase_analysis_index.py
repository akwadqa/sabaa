# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

"""Demand planning from consumption rates.

Sales of the months before From Date give the average monthly consumption. Stock cover and the
suggested order qty follow from it. Quantities are in the selected UOM. An item without a conversion
to that UOM is shown in its stock UOM.
"""

from datetime import date

import frappe
from frappe import _
from frappe.query_builder.functions import Min
from frappe.utils import (
	add_days,
	add_months,
	ceil,
	cint,
	date_diff,
	escape_html,
	flt,
	get_first_day,
	getdate,
)

from sabaa.sabaa.report.purchase_analysis_index.item_activity import ItemActivity

DEFAULT_SALES_MONTHS = 3
MAX_SALES_MONTHS = 12
DEFAULT_TARGET_MONTHS = 2
LINK_FILTERS = {
	"uom": "UOM",
	"supplier": "Supplier",
	"item_group": "Item Group",
	"item_code": "Item",
	"warehouse": "Warehouse",
}

ORDER = "Order"
OK = "OK"
OVERSTOCK = "Overstock"
NO_SALES = "No Sales"


def execute(filters: dict | None = None):
	return PurchaseAnalysisIndex(filters).run()


class PurchaseAnalysisIndex:
	def __init__(self, filters: dict | None):
		self.filters = frappe._dict(filters or {})
		if not (self.filters.from_date and self.filters.to_date and self.filters.uom):
			frappe.throw(_("From Date, Stock As Of and UOM are required"))

		self.from_date = getdate(self.filters.from_date)
		self.to_date = getdate(self.filters.to_date)
		self.uom = self.filters.uom
		self.sales_months = cint(self.filters.sales_months) or DEFAULT_SALES_MONTHS
		self.target_months = flt(self.filters.target_months) or DEFAULT_TARGET_MONTHS
		self.show_details = cint(self.filters.show_details)
		self.validate()

		self.current_month_start = getdate(get_first_day(self.to_date))
		self.window = SalesWindow(self.from_date, self.sales_months, get_go_live_date())
		self.settings = frappe.get_cached_doc("Purchase Analysis Settings")
		self.warehouse_groups = self.get_warehouse_groups() if self.show_details else []

	def validate(self):
		self.validate_link_filters()
		if self.to_date < self.from_date:
			frappe.throw(_("Stock As Of date cannot be before From Date"))
		if not 1 <= self.sales_months <= MAX_SALES_MONTHS:
			frappe.throw(
				_("Sales Months must be between 1 and {0}, not {1}").format(
					MAX_SALES_MONTHS, self.sales_months
				)
			)
		if self.target_months < 0:
			frappe.throw(_("Target Cover (Months) cannot be negative"))

	def validate_link_filters(self):
		"""Filters come from the URL. The UOM shows in card labels and every value reaches SQL."""
		for fieldname, doctype in LINK_FILTERS.items():
			value = self.filters.get(fieldname)
			if value and not (isinstance(value, str) and frappe.db.exists(doctype, value)):
				frappe.throw(
					_("{0} {1} does not exist").format(_(doctype), escape_html(str(value))),
					frappe.DoesNotExistError,
				)

	def get_warehouse_groups(self) -> list[frappe._dict]:
		groups = (
			("main_qty", _("Main Store Qty"), 100, self.settings.main_store_warehouse),
			("van_qty", _("Vans Qty"), 90, self.settings.van_sales_warehouse),
		)
		return [
			frappe._dict(fieldname=fieldname, label=label, width=width, warehouse=warehouse)
			for fieldname, label, width, warehouse in groups
			if warehouse
		]

	def run(self):
		activity = ItemActivity(self)
		rows = [row for item in activity.items if (row := self.get_row(item, activity))]
		rows.sort(key=lambda row: (row["item_group"] or "", row["item_name"] or ""))
		return self.get_columns(), rows, None, None, self.get_summary(rows)

	def get_row(self, item: dict, activity: ItemActivity) -> dict | None:
		movement = activity.movements.get(item.item_code) or {}
		open_order = activity.open_orders.get(item.item_code) or {}
		last_receipt = activity.last_receipts.get(item.item_code) or {}
		purchased = flt((activity.purchases.get(item.item_code) or {}).get("qty"))

		sales = [flt(movement.get(f"sales_{number}")) for number in range(1, self.sales_months + 1)]
		closing = flt(movement.get("closing"))
		pending = flt(open_order.get("pending"))
		opening, sold = flt(movement.get("opening")), flt(movement.get("sold"))
		if not (any(sales) or opening or closing or purchased or sold or pending):
			return None

		factor, row_uom = self.get_conversion(item)
		safety_stock = flt(item.safety_stock)
		plan = self.get_plan(sum(sales), closing, pending, safety_stock, factor)
		if self.filters.only_to_order and plan.status != ORDER:
			return None

		row = {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"item_group": item.item_group,
			"uom": row_uom,
			"uom_fallback": cint(row_uom != self.uom),
			**{f"sales_{number}": flt(qty / factor, 2) for number, qty in enumerate(sales, start=1)},
			"current_month_sales": flt(flt(movement.get("current_month_sales")) / factor, 2),
			"avg": flt(plan.avg / factor, 2),
			"closing": flt(closing / factor, 2),
			"on_order": flt(pending / factor, 2),
			"eta": open_order.get("eta"),
			"cover": flt(plan.cover, 1) if plan.cover is not None else None,
			"cover_all": flt(plan.cover_all, 1) if plan.cover_all is not None else None,
			"min_stock": flt(safety_stock / factor, 2),
			"required": flt(plan.required / factor, 2),
			"suggested": plan.suggested,
			"status": plan.status,
			"last_supplier": last_receipt.get("supplier"),
			"last_date": last_receipt.get("posting_date"),
			"last_qty": flt(flt(last_receipt.get("stock_qty")) / factor, 2),
		}
		if self.show_details:
			row.update(self.get_detail_values(item, activity, factor))
		return row

	def get_conversion(self, item: dict) -> tuple[float, str]:
		"""Factor from the stock UOM to the shown UOM, and the shown UOM."""
		if self.uom == item.stock_uom:
			return 1.0, self.uom
		if item.cf:
			return flt(item.cf), self.uom
		return 1.0, item.stock_uom

	def get_plan(
		self, total_sales: float, closing: float, pending: float, safety_stock: float, factor: float
	) -> frappe._dict:
		"""Consumption rate, cover and order suggestion. Only the suggestion is in the shown UOM."""
		data_months = self.window.data_months
		# Returns above sales count as no demand.
		avg = max(total_sales / data_months if data_months > 0 else 0, 0)
		required = avg * self.target_months
		available = closing + pending
		suggested = ceil(flt(max(required + safety_stock - available, 0) / factor, 6))
		cover_all = available / avg if avg > 0 else None
		return frappe._dict(
			avg=avg,
			required=required,
			suggested=suggested,
			cover=closing / avg if avg > 0 else None,
			cover_all=cover_all,
			status=self.get_status(suggested, avg, cover_all),
		)

	def get_status(self, suggested: int, avg: float, cover_all: float | None) -> str:
		if suggested > 0:
			return ORDER
		if avg <= 0:
			return NO_SALES
		if cover_all > 2 * self.target_months:
			return OVERSTOCK
		return OK

	def get_detail_values(self, item: dict, activity: ItemActivity, factor: float) -> dict:
		movement = activity.movements.get(item.item_code) or {}
		purchase = activity.purchases.get(item.item_code) or {}
		suppliers = activity.supplier_lists.get(item.item_code) or {}
		last_rate = flt((activity.last_receipts.get(item.item_code) or {}).get("valuation_rate"))
		purchased_qty, purchased_value = flt(purchase.get("qty")), flt(purchase.get("value"))
		sold = flt(movement.get("sold"))
		other_movement = flt(movement.get("period_qty")) - flt(movement.get("purchased_all")) + sold

		values = {
			"cf": factor,
			"last_cost": flt(last_rate * factor, 2),
			"supplier_count": suppliers.get("count") or 0,
			"suppliers": suppliers.get("names"),
			"opening": flt(flt(movement.get("opening")) / factor, 2),
			"purchased": flt(purchased_qty / factor, 2),
			"purchase_cost": flt(purchased_value, 2),
			"avg_cost": flt(purchased_value / (purchased_qty / factor), 2) if purchased_qty else 0,
			"sold": flt(sold / factor, 2),
			"other": flt(other_movement / factor, 2),
			"stock_value": flt(movement.get("closing_value"), 2),
			"po_count": (activity.open_orders.get(item.item_code) or {}).get("po_count") or 0,
		}

		other_warehouses = flt(movement.get("closing"))
		for group in self.warehouse_groups:
			group_qty = flt(movement.get(group.fieldname))
			values[group.fieldname] = flt(group_qty / factor, 2)
			other_warehouses -= group_qty
		values["other_wh_qty"] = flt(other_warehouses / factor, 2)
		return values

	def get_columns(self) -> list[dict]:
		sales_columns = [
			qty_column(_("Sales {0}").format(bucket.label), f"sales_{number}", 105)
			for number, bucket in enumerate(self.window.buckets, start=1)
		]
		columns = [
			link_column(_("Item"), "item_code", "Item", 120),
			{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 230},
			link_column(_("Item Group"), "item_group", "Item Group", 120),
			link_column(_("UOM"), "uom", "UOM", 60),
			*sales_columns,
			qty_column(_("Sales {0} MTD").format(month_label(self.to_date)), "current_month_sales", 115),
			qty_column(self.get_average_label(), "avg", 130),
			qty_column(_("Current Stock"), "closing", 105),
			qty_column(_("On Order"), "on_order", 95),
			{"label": _("Next ETA"), "fieldname": "eta", "fieldtype": "Date", "width": 95},
			qty_column(_("Stock Cover (Months)"), "cover", 100, precision=1),
			qty_column(_("Cover incl. On Order (Months)"), "cover_all", 120, precision=1),
			qty_column(_("Min Stock"), "min_stock", 90),
			qty_column(_("Required for Target"), "required", 115),
			{"label": _("Suggested Order Qty"), "fieldname": "suggested", "fieldtype": "Int", "width": 120},
			{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
			link_column(_("Last Supplier"), "last_supplier", "Supplier", 190),
			{"label": _("Last Receipt Date"), "fieldname": "last_date", "fieldtype": "Date", "width": 100},
			qty_column(_("Last Receipt Qty"), "last_qty", 100),
		]
		if self.show_details:
			columns += self.get_detail_columns()
		return columns

	def get_average_label(self) -> str:
		label = _("Avg Monthly Consumption")
		if self.window.data_months < self.sales_months:
			label += f" ({self.window.data_months} mo data)"
		return label

	def get_detail_columns(self) -> list[dict]:
		return [
			qty_column(_("Conv. Factor"), "cf", 80),
			currency_column(_("Last Landed Cost / UOM"), "last_cost", 120),
			{"label": _("No. of Suppliers"), "fieldname": "supplier_count", "fieldtype": "Int", "width": 90},
			{"label": _("All Suppliers"), "fieldname": "suppliers", "fieldtype": "Data", "width": 220},
			qty_column(_("Opening Qty"), "opening", 100),
			qty_column(_("Purchased Qty"), "purchased", 100),
			currency_column(_("Purchase Cost"), "purchase_cost", 120),
			currency_column(_("Avg Cost / UOM"), "avg_cost", 100),
			qty_column(_("Sold Qty (Period)"), "sold", 105),
			qty_column(_("Other Movement"), "other", 100),
			*(qty_column(group.label, group.fieldname, group.width) for group in self.warehouse_groups),
			qty_column(_("Other Warehouses Qty"), "other_wh_qty", 110),
			currency_column(_("Stock Value"), "stock_value", 120),
			{"label": _("Open POs"), "fieldname": "po_count", "fieldtype": "Int", "width": 75},
		]

	def get_summary(self, rows: list[dict]) -> list[dict]:
		"""Summary cards. A card with a row_filter shows only the matching rows when clicked."""

		def count(status):
			return sum(1 for row in rows if row["status"] == status)

		return [
			summary_card(_("Sales Window"), self.window.label, "Blue", datatype="Data"),
			summary_card(_("Months with Data"), self.window.data_months, "Blue", datatype="Float"),
			summary_card(_("Items to Order"), count(ORDER), "Red", {"status": ORDER}),
			summary_card(
				_("Suggested Qty ({0})").format(self.uom),
				sum(row["suggested"] for row in rows if not row["uom_fallback"]),
				"Red",
				{"status": ORDER, "uom_fallback": 0},
				datatype="Float",
			),
			summary_card(_("Overstock Items"), count(OVERSTOCK), "Orange", {"status": OVERSTOCK}),
			summary_card(_("No Sales Items"), count(NO_SALES), "Grey", {"status": NO_SALES}),
			summary_card(
				_("Items Not in {0} (excluded from qty)").format(self.uom),
				sum(row["uom_fallback"] for row in rows),
				"Orange",
				{"uom_fallback": 1},
			),
		]


class SalesWindow:
	"""Whole-month sales buckets that end the day before From Date, oldest first."""

	def __init__(self, from_date: date, months: int, go_live: date | None):
		self.from_date = from_date
		self.buckets = [self.get_bucket(months_back) for months_back in range(months, 0, -1)]
		# Days before go-live have no data, so they do not count as months in the average.
		self.data_months = flt(sum(get_data_share(bucket, go_live) for bucket in self.buckets), 2)

	@property
	def is_calendar_months(self) -> bool:
		return self.from_date.day == 1

	@property
	def label(self) -> str:
		if self.is_calendar_months:
			return f"{self.buckets[0].label} to {self.buckets[-1].label}"

		start, end = self.buckets[0].start, self.buckets[-1].end
		return f"{day_label(start)}-{start.year} to {day_label(end)}-{end.year}"

	def get_bucket(self, months_back: int) -> frappe._dict:
		start = getdate(add_months(self.from_date, -months_back))
		end = getdate(add_days(add_months(self.from_date, -months_back + 1), -1))
		label = month_label(start) if self.is_calendar_months else f"{day_label(start)} to {day_label(end)}"
		return frappe._dict(start=start, end=end, label=label)


def get_data_share(bucket: frappe._dict, go_live: date | None) -> float:
	"""Share of the bucket's days on or after go-live."""
	start = max(bucket.start, go_live) if go_live else bucket.start
	covered_days = max(date_diff(bucket.end, start) + 1, 0)
	return covered_days / (date_diff(bucket.end, bucket.start) + 1)


def get_go_live_date() -> date | None:
	"""Date of the first stock transaction."""
	sle = frappe.qb.DocType("Stock Ledger Entry")
	first = frappe.qb.from_(sle).select(Min(sle.posting_date)).where(sle.is_cancelled == 0).run()[0][0]
	return getdate(first) if first else None


def month_label(day: date) -> str:
	return f"{day:%b-%Y}"


def day_label(day: date) -> str:
	return f"{day.day}-{day:%b}"


def link_column(label: str, fieldname: str, options: str, width: int) -> dict:
	# The report runner rejects all rows when the user cannot read a linked doctype
	# (e.g. System Manager on Supplier), so show those links as plain text.
	if not frappe.has_permission(options, "read"):
		return {"label": label, "fieldname": fieldname, "fieldtype": "Data", "width": width}
	return {"label": label, "fieldname": fieldname, "fieldtype": "Link", "options": options, "width": width}


def qty_column(label: str, fieldname: str, width: int, precision: int = 2) -> dict:
	return {
		"label": label,
		"fieldname": fieldname,
		"fieldtype": "Float",
		"precision": precision,
		"width": width,
	}


def currency_column(label: str, fieldname: str, width: int) -> dict:
	return {"label": label, "fieldname": fieldname, "fieldtype": "Currency", "width": width}


def summary_card(label, value, indicator: str, row_filter: dict | None = None, datatype: str = "Int") -> dict:
	card = {"label": label, "value": value, "datatype": datatype, "indicator": indicator}
	if row_filter:
		card["row_filter"] = row_filter
	return card
