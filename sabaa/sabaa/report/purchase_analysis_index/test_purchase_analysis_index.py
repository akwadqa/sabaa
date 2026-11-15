# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from erpnext.stock.doctype.item.test_item import make_item
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, get_first_day, getdate, today

from sabaa.sabaa.report.purchase_analysis_index.purchase_analysis_index import (
	SalesWindow,
	execute,
	link_column,
)

COMPANY = "Saba Trading Group"
SETTINGS = "Purchase Analysis Settings"


class TestSalesWindow(FrappeTestCase):
	def test_calendar_months_end_the_day_before_from_date(self):
		window = SalesWindow(getdate("2026-11-01"), 3, go_live=None)

		self.assertEqual([bucket.label for bucket in window.buckets], ["Aug-2026", "Sep-2026", "Oct-2026"])
		self.assertEqual(window.buckets[-1].end, getdate("2026-10-31"))
		self.assertEqual(window.label, "Aug-2026 to Oct-2026")
		self.assertEqual(window.data_months, 3)

	def test_mid_month_from_date_gives_day_ranges(self):
		window = SalesWindow(getdate("2026-10-15"), 3, go_live=None)

		self.assertEqual(window.buckets[0].label, "15-Jul to 14-Aug")
		self.assertEqual(window.label, "15-Jul-2026 to 14-Oct-2026")

	def test_window_can_cover_more_than_three_months(self):
		window = SalesWindow(getdate("2026-11-01"), 12, go_live=None)

		self.assertEqual(len(window.buckets), 12)
		self.assertEqual(window.buckets[0].start, getdate("2025-11-01"))
		self.assertEqual(window.data_months, 12)

	def test_days_before_go_live_do_not_count_as_months(self):
		window = SalesWindow(getdate("2026-07-01"), 3, go_live=getdate("2026-05-16"))

		# April has no data, May has 16 of its 31 days, June is complete.
		self.assertEqual(window.data_months, 1.52)


class TestLinkColumn(FrappeTestCase):
	def test_link_the_user_cannot_read_becomes_plain_text(self):
		with patch(
			"frappe.has_permission", side_effect=lambda doctype, *args, **kwargs: doctype != "Supplier"
		):
			supplier = link_column("Last Supplier", "last_supplier", "Supplier", 190)
			item = link_column("Item", "item_code", "Item", 120)

		self.assertEqual(supplier["fieldtype"], "Data")
		self.assertNotIn("options", supplier)
		self.assertEqual((item["fieldtype"], item["options"]), ("Link", "Item"))


class TestPurchaseAnalysisIndex(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase only rolls back at class teardown; the tests post real stock transactions.
		self._savepoint = "test_purchase_analysis_index"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(frappe.clear_document_cache, SETTINGS, SETTINGS)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

		self.warehouse = frappe.get_all(
			"Warehouse", filters={"company": COMPANY, "is_group": 0}, pluck="name", limit=1
		)[0]
		self.customer = frappe.get_all("Customer", filters={"disabled": 0}, pluck="name", limit=1)[0]
		# Driver is mandatory on Delivery Note on this site.
		self.driver = frappe.get_all("Driver", filters={"status": "Active"}, pluck="name", limit=1)[0]
		self.from_date = getdate(get_first_day(today()))

		settings = frappe.get_single(SETTINGS)
		settings.promotional_name_markers = "G.P"
		settings.set("promotional_uoms", [{"uom": "Box"}])
		settings.save()

	def test_sales_stock_and_suggested_qty_in_selected_uom(self):
		item = self.make_stock_item("PAI Test Juice 1x12")
		self.receive(item, 240, add_months(self.from_date, -4))
		for months_back, qty in ((3, 24), (2, 36), (1, 60)):
			self.deliver(item, qty, add_days(add_months(self.from_date, -months_back), 4))
		self.deliver(item, 12, today())

		_columns, rows, _message, _chart, summary = self.run_report(item_code=item, target_months=3)

		# 120 Nos sold in 3 months = 40 Nos a month. Stock 108 Nos, target 3 months = 120 Nos.
		expected = {
			"uom": "Ctn",
			"uom_fallback": 0,
			"sales_1": 2,
			"sales_2": 3,
			"sales_3": 5,
			"current_month_sales": 1,
			"avg": 3.33,
			"closing": 9,
			"cover": 2.7,
			"required": 10,
			"suggested": 1,
			"status": "Order",
		}
		self.assertEqual({key: rows[0][key] for key in expected}, expected)

		cards = {card["label"]: card for card in summary}
		self.assertEqual(cards["Items to Order"]["value"], 1)
		self.assertEqual(cards["Items to Order"]["row_filter"], {"status": "Order"})
		self.assertEqual(cards["Suggested Qty (Ctn)"]["value"], 1)

	def test_item_without_conversion_is_shown_in_stock_uom(self):
		item = self.make_stock_item("PAI Test Water 1x24")
		self.receive(item, 48, add_months(self.from_date, -2))

		_columns, rows, _message, _chart, summary = self.run_report(item_code=item, uom="Pcs")

		self.assertEqual((rows[0]["uom"], rows[0]["uom_fallback"], rows[0]["closing"]), ("Nos", 1, 48))
		cards = {card["label"]: card for card in summary}
		self.assertEqual(cards["Items Not in Pcs (excluded from qty)"]["value"], 1)

	def test_promotional_items_are_left_out(self):
		marked = self.make_stock_item("PAI Test Chips 1x24x15gm-g.p")
		boxed = self.make_stock_item("PAI Test Maamoul 1x12x300gm", stock_uom="Box")
		for item in (marked, boxed):
			self.receive(item, 10, add_days(self.from_date, -10))

		for item in (marked, boxed):
			self.assertEqual(self.run_report(item_code=item)[1], [])

	def test_sales_months_extends_the_window(self):
		item = self.make_stock_item("PAI Test Dates 1x12")
		self.receive(item, 240, add_months(self.from_date, -7))
		self.deliver(item, 12, add_days(add_months(self.from_date, -5), 4))

		columns, rows, *_ = self.run_report(item_code=item, sales_months=6)

		sales_fields = [column["fieldname"] for column in columns if column["fieldname"].startswith("sales_")]
		self.assertEqual(sales_fields, [f"sales_{number}" for number in range(1, 7)])
		# The sale is 5 months back, the second bucket of six. 12 Nos over 6 months = 1/6 Ctn a month.
		self.assertEqual((rows[0]["sales_2"], rows[0]["avg"]), (1, 0.17))

	def test_invalid_filters_are_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.run_report(sales_months=13)
		with self.assertRaises(frappe.ValidationError):
			self.run_report(to_date=add_days(self.from_date, -1))

	def test_link_filters_must_name_an_existing_record(self):
		# The UOM shows in summary card labels, so it must not carry markup.
		with self.assertRaises(frappe.DoesNotExistError):
			self.run_report(uom='<img src=x onerror="alert(1)">')
		with self.assertRaises(frappe.DoesNotExistError):
			self.run_report(warehouse=["!=", ""])

	def run_report(self, **filters):
		return execute(
			{"from_date": self.from_date, "to_date": today(), "uom": "Ctn", "target_months": 2, **filters}
		)

	def make_stock_item(self, item_name: str, stock_uom: str = "Nos") -> str:
		uoms = [{"uom": stock_uom, "conversion_factor": 1}]
		if stock_uom == "Nos":
			uoms.append({"uom": "Ctn", "conversion_factor": 12})
		item = make_item(
			properties={
				"item_name": item_name,
				"item_group": "Canned Food",
				"is_stock_item": 1,
				"stock_uom": stock_uom,
				"uoms": uoms,
			}
		)
		return item.name

	def receive(self, item: str, qty: float, posting_date):
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = stock_entry.purpose = "Material Receipt"
		stock_entry.company = COMPANY
		stock_entry.posting_date = posting_date
		stock_entry.set_posting_time = 1
		stock_entry.append(
			"items", {"item_code": item, "t_warehouse": self.warehouse, "qty": qty, "basic_rate": 5}
		)
		stock_entry.insert()
		stock_entry.submit()

	def deliver(self, item: str, qty: float, posting_date):
		delivery_note = frappe.new_doc("Delivery Note")
		delivery_note.company = COMPANY
		delivery_note.customer = self.customer
		delivery_note.driver = self.driver
		delivery_note.posting_date = posting_date
		delivery_note.set_posting_time = 1
		delivery_note.append(
			"items", {"item_code": item, "warehouse": self.warehouse, "qty": qty, "rate": 10}
		)
		delivery_note.insert()
		delivery_note.submit()
