# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from sabaa.sabaa.commission.sources import (
	BasisRow,
	DeliveryRow,
	get_delivery_fees,
	get_tender_collections,
	get_units,
)
from sabaa.sabaa.commission.tests.factories import (
	make_account,
	make_carton_item,
	make_customer,
	make_customer_group,
	make_driver,
	make_employee,
	make_journal_entry,
	make_qty_invoice,
	make_sales_invoice,
	make_sales_person,
	make_service_item,
)

COMPANY = "Saba Trading Group"
MAY = getdate("2026-05-01")
JUNE = getdate("2026-06-01")


class TestOtherSources(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_sources_other"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

		self.group = make_customer_group("Test Online Group")
		self.customer = make_customer("Test Online Customer", self.group)
		self.sales_person = make_sales_person("Test Online SP")
		self.item = make_service_item("TEST-ONLINE-GOODS")
		self.delivery_account = make_account("Test Delivery Charges", is_collection=False)

	def online_invoice(self, driver, delivery_fee=None, posting_date="2026-05-10"):
		taxes = [(self.delivery_account, delivery_fee)] if delivery_fee else []
		return make_sales_invoice(
			self.customer,
			self.sales_person,
			posting_date,
			[(self.item, 100)],
			taxes=taxes,
			extra={"driver": driver},
		)

	def delivery(self):
		return get_delivery_fees(COMPANY, [self.group], "2026-05-01", "2026-05-31", self.delivery_account)

	def test_delivery_fees_and_free_orders_per_driver(self):
		employee = make_employee("Test Delivery Driver")
		driver = make_driver("Test Delivery Driver", employee)
		self.online_invoice(driver, 15)
		self.online_invoice(driver, 15)
		self.online_invoice(driver)

		self.assertEqual(self.delivery(), [DeliveryRow(MAY, driver, employee, 30, 1)])

	def test_driver_without_employee(self):
		driver = make_driver("Test Unlinked Driver")
		self.online_invoice(driver, 15)

		self.assertEqual(self.delivery(), [DeliveryRow(MAY, driver, None, 15, 0)])

	def test_units_converted_to_cartons(self):
		item = make_carton_item("TEST-TEA-MILK", 48)
		make_qty_invoice(self.customer, self.sales_person, "2026-05-12", item, 96, 2)
		rates = [frappe._dict(item=item, uom="Ctn", amount_per_unit=1)]

		rows = get_units(COMPANY, [self.group], "2026-05-01", "2026-05-31", rates, "Ctn")

		self.assertEqual(rows, [BasisRow(MAY, self.sales_person, 2)])

	def test_unit_returns_are_negative(self):
		item = make_carton_item("TEST-TEA-MILK-RET", 48)
		make_qty_invoice(self.customer, self.sales_person, "2026-05-12", item, 96, 2)
		make_qty_invoice(self.customer, self.sales_person, "2026-05-13", item, -48, 2)
		rates = [frappe._dict(item=item, uom="Ctn", amount_per_unit=1)]

		rows = get_units(COMPANY, [self.group], "2026-05-01", "2026-05-31", rates, "Ctn")

		self.assertEqual(rows, [BasisRow(MAY, self.sales_person, 1)])

	def test_tender_collections_counted_in_month_received(self):
		collection = make_account("Test Tender Cash", is_collection=True)
		tender = make_sales_invoice(
			self.customer, self.sales_person, "2026-05-05", [(self.item, 100000)], extra={"is_tender": 1}
		)
		regular = make_sales_invoice(self.customer, self.sales_person, "2026-05-05", [(self.item, 500)])
		make_journal_entry(self.customer, "2026-06-10", 50000, collection, ("Sales Invoice", tender))
		make_journal_entry(self.customer, "2026-06-11", 500, collection, ("Sales Invoice", regular))

		rows = get_tender_collections(COMPANY, "2026-05-01", "2026-06-30")

		self.assertEqual(rows, [BasisRow(JUNE, None, 50000)])
