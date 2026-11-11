"""Set-based readers for the money basis of sales commissions: one query per source per date range."""

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import frappe
from frappe.query_builder import DocType, Tuple
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import flt, getdate

from sabaa.sabaa.commission.periods import month_start

ATTRIBUTED_BY_CUSTOMER = "attributed by customer"
OPENING_BALANCE = "opening balance"
NO_SALES_PERSON = "no sales person"

COLLECTION_VOUCHER_TYPES = ("Payment Entry", "Journal Entry")

SalesInvoice = DocType("Sales Invoice")
SalesTeam = DocType("Sales Team")
Customer = DocType("Customer")
# Invoices without a Sales Team row count in full (to "no sales person").
SALES_TEAM_SHARE = Coalesce(SalesTeam.allocated_percentage, 100) / 100


@dataclass(frozen=True)
class BasisRow:
	month: date
	key: str | None
	amount: float
	flag: str | None = None


BucketKey = tuple[date, str | None, str | None]


def expand_customer_groups(groups: list[str], excluded: list[str]) -> list[str]:
	removed = set(_get_group_subtree(excluded))
	return [group for group in _get_group_subtree(groups) if group not in removed]


def _get_group_subtree(groups: list[str]) -> list[str]:
	if not groups:
		return []

	node, root = DocType("Customer Group"), DocType("Customer Group").as_("root")
	return (
		frappe.qb.from_(node)
		.join(root)
		.on((node.lft >= root.lft) & (node.rgt <= root.rgt))
		.where(root.name.isin(groups))
		.select(node.name)
		.distinct()
		.orderby(node.lft)
		.run(pluck=True)
	)


def get_invoiced(
	company: str,
	customer_groups: list[str],
	from_date: date | str,
	to_date: date | str,
	exclude_items: Iterable[str] = (),
) -> list[BasisRow]:
	"""Net invoiced amount per posting month and invoice sales person; returns count negative.

	Groups are matched on the invoice's stored customer group; opening invoices are left out.
	"""
	if not customer_groups:
		return []

	totals: dict[BucketKey, float] = defaultdict(float)
	query = _invoice_query(company, customer_groups, from_date, to_date)
	for row in _sum_by_sales_person(query, SalesInvoice.base_net_total):
		totals[_invoice_bucket(row)] += row.amount

	_subtract_item_amounts(totals, company, customer_groups, from_date, to_date, exclude_items)
	return _to_rows(totals)


def get_collected(
	company: str,
	customer_groups: list[str],
	from_date: date | str,
	to_date: date | str,
	exclude_items: Iterable[str] = (),
) -> list[BasisRow]:
	"""Customer collections per payment month, attributed to a sales person (see design §6.2).

	"Latest invoice before the payment date" means on or before it: cash customers pay on the invoice day.
	"""
	if not customer_groups:
		return []

	totals: dict[BucketKey, float] = defaultdict(float)
	_add_ledger_collections(totals, company, customer_groups, from_date, to_date)

	pos_invoices = _invoice_query(company, customer_groups, from_date, to_date)
	pos_paid = SalesInvoice.base_paid_amount - SalesInvoice.base_change_amount
	# POS returns are refunds, and refunds do not reduce collections (business default G1).
	pos_sales = pos_invoices.where((SalesInvoice.is_pos == 1) & (SalesInvoice.is_return == 0))
	for row in _sum_by_sales_person(pos_sales, pos_paid):
		totals[_invoice_bucket(row)] += row.amount

	_subtract_item_amounts(totals, company, customer_groups, from_date, to_date, exclude_items)
	return _to_rows(totals)


def _add_ledger_collections(
	totals: dict[BucketKey, float],
	company: str,
	customer_groups: list[str],
	from_date: date | str,
	to_date: date | str,
) -> None:
	rows = _get_ledger_collections(company, customer_groups, from_date, to_date)
	history = InvoiceHistory.load(company, {row.party for row in rows}, to_date)
	is_counting_opening = frappe.db.get_single_value(
		"Commission Settings", "count_opening_balance_collections"
	)

	for row in rows:
		if "Yes" in (row.journal_opening, row.invoice_opening):
			if not is_counting_opening:
				continue
			key, flag = history.get_bucket(row.party, row.posting_date, OPENING_BALANCE)
		elif row.against_voucher_type == "Sales Invoice":
			key, flag = _sales_person_bucket(row.sales_person)
		else:
			key, flag = history.get_bucket(row.party, row.posting_date, ATTRIBUTED_BY_CUSTOMER)
		totals[(month_start(row.posting_date), key, flag)] += row.amount


def _get_ledger_collections(
	company: str, customer_groups: list[str], from_date: date | str, to_date: date | str
) -> list[frappe._dict]:
	"""Customer credits from vouchers that touch a collection account, summed per date/party/target.

	Allocated rows match on the invoice's stored customer group; others on the customer's current group.
	"""
	ledger, against_journal = DocType("Payment Ledger Entry"), DocType("Journal Entry")
	against_invoice = SalesInvoice.as_("against_invoice")
	query = (
		frappe.qb.from_(ledger)
		.join(Customer)
		.on(Customer.name == ledger.party)
		.left_join(SalesTeam)
		.on(
			(ledger.against_voucher_type == "Sales Invoice")
			& (SalesTeam.parenttype == "Sales Invoice")
			& (SalesTeam.parent == ledger.against_voucher_no)
		)
		.left_join(against_invoice)
		.on(
			(ledger.against_voucher_type == "Sales Invoice")
			& (against_invoice.name == ledger.against_voucher_no)
		)
		.left_join(against_journal)
		.on(
			(ledger.against_voucher_type == "Journal Entry")
			& (against_journal.name == ledger.against_voucher_no)
		)
		.where(_customer_collection_condition(ledger, company, from_date, to_date))
		.where(Coalesce(against_invoice.customer_group, Customer.customer_group).isin(customer_groups))
	)
	return (
		query.select(
			ledger.posting_date,
			ledger.party,
			ledger.against_voucher_type,
			SalesTeam.sales_person,
			against_journal.is_opening.as_("journal_opening"),
			against_invoice.is_opening.as_("invoice_opening"),
			Sum(-ledger.amount * SALES_TEAM_SHARE).as_("amount"),
		)
		.groupby(
			ledger.posting_date,
			ledger.party,
			ledger.against_voucher_type,
			SalesTeam.sales_person,
			against_journal.is_opening,
			against_invoice.is_opening,
		)
		.run(as_dict=True)
	)


def _customer_collection_condition(ledger, company: str, from_date: date | str, to_date: date | str):
	return (
		(ledger.company == company)
		& (ledger.party_type == "Customer")
		& (ledger.delinked == 0)
		& (ledger.amount < 0)
		& ledger.posting_date[getdate(from_date) : getdate(to_date)]
		& Tuple(ledger.voucher_type, ledger.voucher_no).isin(
			_collection_vouchers_query(company, from_date, to_date)
		)
	)


def _collection_vouchers_query(company: str, from_date: date | str, to_date: date | str):
	"""Non-opening Payment/Journal Entries with a GL row on one of the company's collection accounts."""
	gl = DocType("GL Entry")
	collection_account = DocType("Sales Collection Account")
	return (
		frappe.qb.from_(gl)
		.join(collection_account)
		.on(collection_account.sales_collection_account == gl.account)
		.where(
			(collection_account.parenttype == "Company")
			& (collection_account.parentfield == "sales_collection_accounts")
			& (collection_account.parent == company)
			& (gl.company == company)
			& (gl.is_cancelled == 0)
			& (gl.is_opening == "No")
			& gl.voucher_type.isin(COLLECTION_VOUCHER_TYPES)
			& gl.posting_date[getdate(from_date) : getdate(to_date)]
		)
		.select(gl.voucher_type, gl.voucher_no)
		.distinct()
	)


class InvoiceHistory:
	"""Sales person of each customer's latest non-return, non-opening invoice on or before a date."""

	def __init__(self, invoices: list[frappe._dict]):
		self._dates: dict[str, list[date]] = defaultdict(list)
		self._sales_persons: dict[str, list[str | None]] = defaultdict(list)
		for invoice in invoices:
			self._dates[invoice.customer].append(invoice.posting_date)
			self._sales_persons[invoice.customer].append(invoice.sales_person)

	@classmethod
	def load(cls, company: str, customers: set[str], to_date: date | str) -> "InvoiceHistory":
		if not customers:
			return cls([])

		invoices = (
			frappe.qb.from_(SalesInvoice)
			.left_join(SalesTeam)
			.on((SalesTeam.parenttype == "Sales Invoice") & (SalesTeam.parent == SalesInvoice.name))
			.where(
				(SalesInvoice.docstatus == 1)
				& (SalesInvoice.company == company)
				& (SalesInvoice.is_return == 0)
				& (SalesInvoice.is_opening == "No")
				& SalesInvoice.customer.isin(list(customers))
				& (SalesInvoice.posting_date <= getdate(to_date))
			)
			.select(SalesInvoice.customer, SalesInvoice.posting_date, SalesTeam.sales_person)
			.orderby(SalesInvoice.posting_date)
			.orderby(SalesInvoice.posting_time)
			.orderby(SalesInvoice.creation)
			.run(as_dict=True)
		)
		return cls(invoices)

	def get_bucket(self, customer: str, on_date: date, flag: str) -> tuple[str | None, str]:
		position = bisect_right(self._dates[customer], on_date)
		sales_person = self._sales_persons[customer][position - 1] if position else None
		return (sales_person, flag) if sales_person else (None, NO_SALES_PERSON)


def _invoice_query(company: str, customer_groups: list[str], from_date: date | str, to_date: date | str):
	return (
		frappe.qb.from_(SalesInvoice)
		.left_join(SalesTeam)
		.on((SalesTeam.parenttype == "Sales Invoice") & (SalesTeam.parent == SalesInvoice.name))
		.where(
			(SalesInvoice.docstatus == 1)
			& (SalesInvoice.company == company)
			& (SalesInvoice.is_opening == "No")
			& SalesInvoice.posting_date[getdate(from_date) : getdate(to_date)]
			& SalesInvoice.customer_group.isin(customer_groups)
		)
	)


def _sum_by_sales_person(query, amount) -> list[frappe._dict]:
	"""Sum `amount` per posting date and sales person, split by the Sales Team allocation."""
	return (
		query.select(
			SalesInvoice.posting_date, SalesTeam.sales_person, Sum(amount * SALES_TEAM_SHARE).as_("amount")
		)
		.groupby(SalesInvoice.posting_date, SalesTeam.sales_person)
		.run(as_dict=True)
	)


def _subtract_item_amounts(
	totals: dict[BucketKey, float],
	company: str,
	customer_groups: list[str],
	from_date: date | str,
	to_date: date | str,
	exclude_items: Iterable[str],
) -> None:
	exclude_items = list(exclude_items)
	if not exclude_items:
		return

	invoice_item = DocType("Sales Invoice Item")
	query = (
		_invoice_query(company, customer_groups, from_date, to_date)
		.join(invoice_item)
		.on(invoice_item.parent == SalesInvoice.name)
		.where(invoice_item.item_code.isin(exclude_items))
	)
	for row in _sum_by_sales_person(query, invoice_item.base_net_amount):
		totals[_invoice_bucket(row)] -= row.amount


def _invoice_bucket(row: frappe._dict) -> BucketKey:
	return (month_start(row.posting_date), *_sales_person_bucket(row.sales_person))


def _sales_person_bucket(sales_person: str | None) -> tuple[str | None, str | None]:
	return (sales_person, None) if sales_person else (None, NO_SALES_PERSON)


def _to_rows(totals: dict[BucketKey, float]) -> list[BasisRow]:
	return [
		BasisRow(month, key, flt(amount), flag)
		for (month, key, flag), amount in sorted(totals.items(), key=lambda item: _sort_key(item[0]))
	]


def _sort_key(bucket: BucketKey) -> tuple[date, str, str]:
	month, key, flag = bucket
	return (month, key or "", flag or "")


@dataclass(frozen=True)
class DeliveryRow:
	month: date
	driver: str | None
	employee: str | None
	fee_amount: float
	free_order_count: int


def get_delivery_fees(
	company: str, customer_groups: list[str], from_date: date | str, to_date: date | str, account: str
) -> list[DeliveryRow]:
	"""Delivery charges per month and invoice driver; an invoice with no charge is a free order.

	Charges are read from tax rows and item rows booked to `account` (the site uses tax rows).
	"""
	if not customer_groups:
		return []

	driver = DocType("Driver")
	invoices = (
		_invoice_query(company, customer_groups, from_date, to_date)
		.left_join(driver)
		.on(driver.name == SalesInvoice.driver)
		.where(SalesInvoice.is_return == 0)
		.select(SalesInvoice.name, SalesInvoice.posting_date, SalesInvoice.driver, driver.employee)
		.distinct()
		.run(as_dict=True)
	)
	fees = _get_delivery_charges([invoice.name for invoice in invoices], account)

	totals: dict[tuple, list[float]] = defaultdict(lambda: [0.0, 0])
	for invoice in invoices:
		bucket = totals[(month_start(invoice.posting_date), invoice.driver, invoice.employee)]
		fee = fees.get(invoice.name, 0)
		bucket[0] += fee
		bucket[1] += 0 if fee else 1
	return [
		DeliveryRow(month, driver_name, employee, flt(fee), count)
		for (month, driver_name, employee), (fee, count) in sorted(
			totals.items(), key=lambda item: (item[0][0], item[0][1] or "")
		)
	]


def _get_delivery_charges(invoice_names: list[str], account: str) -> dict[str, float]:
	if not invoice_names:
		return {}

	fees: dict[str, float] = defaultdict(float)
	tax, item = DocType("Sales Taxes and Charges"), DocType("Sales Invoice Item")
	sources = (
		(tax, tax.base_tax_amount, tax.account_head, "Sales Invoice"),
		(item, item.base_net_amount, item.income_account, None),
	)
	for table, amount, account_field, parenttype in sources:
		query = frappe.qb.from_(table).where(table.parent.isin(invoice_names) & (account_field == account))
		if parenttype:
			query = query.where(table.parenttype == parenttype)
		for row in query.select(table.parent, Sum(amount).as_("amount")).groupby(table.parent).run(as_dict=True):
			fees[row.parent] += flt(row.amount)
	return fees


def get_units(
	company: str,
	customer_groups: list[str],
	from_date: date | str,
	to_date: date | str,
	unit_rates: list[frappe._dict],
	carton_uom: str,
) -> list[BasisRow]:
	"""Per-unit commission per posting month and sales person: cartons sold × amount per unit.

	Returns count negative (business default U1). A rate's own UOM wins over `carton_uom`.
	"""
	rates = {rate.item: rate for rate in unit_rates}
	if not customer_groups or not rates:
		return []

	invoice_item = DocType("Sales Invoice Item")
	rows = (
		_invoice_query(company, customer_groups, from_date, to_date)
		.join(invoice_item)
		.on(invoice_item.parent == SalesInvoice.name)
		.where(invoice_item.item_code.isin(list(rates)))
		.select(
			SalesInvoice.posting_date,
			SalesTeam.sales_person,
			invoice_item.item_code,
			Sum(invoice_item.stock_qty * SALES_TEAM_SHARE).as_("stock_qty"),
		)
		.groupby(SalesInvoice.posting_date, SalesTeam.sales_person, invoice_item.item_code)
		.run(as_dict=True)
	)
	factors = _get_unit_factors(rates, carton_uom)

	totals: dict[BucketKey, float] = defaultdict(float)
	for row in rows:
		units = flt(row.stock_qty) / factors[row.item_code]
		totals[_invoice_bucket(row)] += units * flt(rates[row.item_code].amount_per_unit)
	return _to_rows(totals)


def _get_unit_factors(rates: dict[str, frappe._dict], carton_uom: str) -> dict[str, float]:
	"""Stock units per counted unit for each rated item; a missing conversion fails loudly."""
	factors = {}
	for item_code, rate in rates.items():
		uom = rate.get("uom") or carton_uom
		factor = frappe.db.get_value("UOM Conversion Detail", {"parent": item_code, "uom": uom}, "conversion_factor")
		if not factor:
			frappe.throw(frappe._("Item {0} has no conversion for UOM {1}.").format(item_code, uom))
		factors[item_code] = flt(factor)
	return factors


def get_tender_collections(company: str, from_date: date | str, to_date: date | str) -> list[BasisRow]:
	"""Collections allocated to tender invoices, per payment month, as one pool (key None)."""
	ledger = DocType("Payment Ledger Entry")
	rows = (
		frappe.qb.from_(ledger)
		.join(SalesInvoice)
		.on((ledger.against_voucher_type == "Sales Invoice") & (SalesInvoice.name == ledger.against_voucher_no))
		.where(_customer_collection_condition(ledger, company, from_date, to_date))
		.where(SalesInvoice.is_tender == 1)
		.select(ledger.posting_date, Sum(-ledger.amount).as_("amount"))
		.groupby(ledger.posting_date)
		.run(as_dict=True)
	)
	totals: dict[BucketKey, float] = defaultdict(float)
	for row in rows:
		totals[(month_start(row.posting_date), None, None)] += row.amount
	return _to_rows(totals)
