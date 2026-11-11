# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from sabaa.sabaa.commission.sources import (
	ATTRIBUTED_BY_CUSTOMER,
	NO_SALES_PERSON,
	OPENING_BALANCE,
	BasisRow,
	expand_customer_groups,
	get_collected,
	get_invoiced,
)
from sabaa.sabaa.commission.tests.factories import (
	make_account,
	make_customer,
	make_customer_group,
	make_journal_entry,
	make_payment_entry,
	make_sales_invoice,
	make_sales_person,
	make_service_item,
)

COMPANY = "Saba Trading Group"
MAY = getdate("2026-05-01")
JUNE = getdate("2026-06-01")


class TestSources(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_sources"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

		self.group = make_customer_group("Test Commission Group")
		self.customer = make_customer("Test Commission Customer", self.group)
		self.sales_person = make_sales_person("Test SP A")
		self.item = make_service_item("TEST-COMMISSION-GOODS")
		self.collection_account = make_account("Test Collection Cash", is_collection=True)
		self.other_account = make_account("Test Non Collection", is_collection=False)

	def invoice(self, posting_date, amount, sales_person=None, **kwargs):
		return make_sales_invoice(
			self.customer, sales_person or self.sales_person, posting_date, [(self.item, amount)], **kwargs
		)

	def invoiced(self, from_date="2026-05-01", to_date="2026-06-30", **kwargs):
		return get_invoiced(COMPANY, [self.group], from_date, to_date, **kwargs)

	def collected(self, from_date="2026-05-01", to_date="2026-06-30", **kwargs):
		return get_collected(COMPANY, [self.group], from_date, to_date, **kwargs)

	def test_expand_customer_groups_includes_descendants_minus_excluded(self):
		parent = make_customer_group("Test Parent Group", is_group=1)
		kept = make_customer_group("Test Kept Group", parent=parent)
		excluded = make_customer_group("Test Excluded Group", parent=parent, is_group=1)
		make_customer_group("Test Excluded Child", parent=excluded)

		self.assertEqual(sorted(expand_customer_groups([parent], [excluded])), sorted([parent, kept]))

	def test_invoiced_nets_returns(self):
		self.invoice("2026-05-03", 10000)
		self.invoice("2026-05-20", 2500, is_return=1)

		self.assertEqual(self.invoiced(), [BasisRow(MAY, self.sales_person, 7500)])

	def test_direct_sales_excluded(self):
		direct_customer = make_customer("Test Direct Customer", "Direct Sales")
		make_sales_invoice(direct_customer, self.sales_person, "2026-05-03", [(self.item, 1000)])
		groups = expand_customer_groups(["All Customer Groups"], ["Direct Sales"])

		rows = get_invoiced(COMPANY, groups, "2026-05-01", "2026-05-31")

		self.assertNotIn("Direct Sales", groups)
		self.assertFalse([row for row in rows if row.key == self.sales_person])

	def test_invoiced_excludes_unit_items(self):
		tea_milk = make_service_item("TEST-COMMISSION-TEA-MILK")
		make_sales_invoice(
			self.customer, self.sales_person, "2026-05-03", [(self.item, 800), (tea_milk, 200)]
		)

		self.assertEqual(self.invoiced(exclude_items=[tea_milk]), [BasisRow(MAY, self.sales_person, 800)])

	def test_negative_month_allowed(self):
		self.invoice("2026-05-03", 1000)
		self.invoice("2026-05-20", 3000, is_return=1)

		self.assertEqual(self.invoiced(), [BasisRow(MAY, self.sales_person, -2000)])

	def test_collected_allocated_payment(self):
		invoice = self.invoice("2026-05-03", 4000)
		make_payment_entry(self.customer, "2026-06-02", 4000, self.collection_account, invoice=invoice)

		self.assertEqual(self.collected(), [BasisRow(JUNE, self.sales_person, 4000)])

	def test_allocated_journal_counts_for_invoice_sales_person(self):
		invoice = self.invoice("2026-05-03", 1500)
		make_journal_entry(
			self.customer, "2026-05-10", 1500, self.collection_account, reference=("Sales Invoice", invoice)
		)

		self.assertEqual(self.collected(), [BasisRow(MAY, self.sales_person, 1500)])

	def test_credit_note_journal_not_collected(self):
		invoice = self.invoice("2026-05-03", 1000)
		make_journal_entry(
			self.customer, "2026-05-10", 300, self.other_account, reference=("Sales Invoice", invoice)
		)

		self.assertEqual(self.collected(), [])

	def test_unallocated_journal_attributed_by_customer(self):
		self.invoice("2026-05-03", 1000, sales_person=make_sales_person("Test SP Old"))
		self.invoice("2026-05-15", 1000)
		self.invoice("2026-06-20", 1000, sales_person=make_sales_person("Test SP Later"))
		make_journal_entry(self.customer, "2026-06-02", 600, self.collection_account)

		self.assertEqual(
			self.collected(), [BasisRow(JUNE, self.sales_person, 600, ATTRIBUTED_BY_CUSTOMER)]
		)

	def test_unallocated_without_any_invoice_has_no_sales_person(self):
		make_journal_entry(self.customer, "2026-06-02", 600, self.collection_account)

		self.assertEqual(self.collected(), [BasisRow(JUNE, None, 600, NO_SALES_PERSON)])

	def test_opening_balance_collection_follows_setting(self):
		opening = make_journal_entry(self.customer, "2026-04-30", -900, self.other_account, is_opening="Yes")
		self.invoice("2026-05-03", 100)
		make_journal_entry(
			self.customer, "2026-05-10", 900, self.collection_account, reference=("Journal Entry", opening)
		)

		frappe.db.set_single_value("Commission Settings", "count_opening_balance_collections", 0)
		self.assertEqual(self.collected(), [])

		frappe.db.set_single_value("Commission Settings", "count_opening_balance_collections", 1)
		self.assertEqual(self.collected(), [BasisRow(MAY, self.sales_person, 900, OPENING_BALANCE)])

	def test_pos_paid_amount_counted(self):
		self.invoice("2026-05-03", 700, pos_account=self.collection_account)

		self.assertEqual(self.collected(), [BasisRow(MAY, self.sales_person, 700)])

	def test_unit_items_removed_from_collected_basis(self):
		tea_milk = make_service_item("TEST-COMMISSION-TEA-MILK")
		invoice = make_sales_invoice(
			self.customer, self.sales_person, "2026-05-03", [(self.item, 800), (tea_milk, 200)]
		)
		make_payment_entry(self.customer, "2026-05-10", 1000, self.collection_account, invoice=invoice)

		self.assertEqual(
			self.collected(exclude_items=[tea_milk]), [BasisRow(MAY, self.sales_person, 800)]
		)
