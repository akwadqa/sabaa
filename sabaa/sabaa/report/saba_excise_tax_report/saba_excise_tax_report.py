# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import flt

# Stock Entry Types used by the business to write off excisable stock that will
# never reach a Sales Invoice (so its Excise Tax can never be recovered from a
# customer). These are existing master data on the site, not introduced here.
EXPIRED_DAMAGED_STOCK_ENTRY_TYPES = ("Damage", "Expiry")


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if not filters.company:
		frappe.throw(_("Please select a Company"))

	account = frappe.get_cached_value("Company", filters.company, "custom_excise_tax_recoverable_account")
	if not account:
		frappe.throw(
			_("Company {0} does not have an Excise Tax Recoverable Account configured.").format(
				frappe.bold(filters.company)
			),
			title=_("Excise Account Not Configured"),
		)

	paid_to_customs, recovered_from_si, gl_rows = get_gl_amounts(filters, account)
	expired_damaged_excise, stock_rows = get_expired_damaged_excise(filters)
	remaining_balance = paid_to_customs - recovered_from_si - expired_damaged_excise

	show_details = bool(filters.show_details)
	columns = get_columns(show_details)

	if show_details:
		data = get_detail_rows(gl_rows, stock_rows)
	else:
		data = [
			{
				"company": filters.company,
				"paid_to_customs": paid_to_customs,
				"recovered_from_si": recovered_from_si,
				"expired_damaged_excise": expired_damaged_excise,
				"remaining_balance": remaining_balance,
			}
		]

	currency = frappe.get_cached_value("Company", filters.company, "default_currency")
	report_summary = [
		{
			"label": _("Paid to Customs"),
			"value": paid_to_customs,
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"label": _("Recovered from Sales Invoices"),
			"value": recovered_from_si,
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"label": _("Expired/Damaged Excise"),
			"value": expired_damaged_excise,
			"datatype": "Currency",
			"currency": currency,
		},
		{
			"label": _("Remaining Balance"),
			"value": remaining_balance,
			"datatype": "Currency",
			"currency": currency,
		},
	]

	return columns, data, None, None, report_summary


def get_gl_amounts(filters, account):
	"""
	The Excise Tax Recoverable Account is a dedicated account (per business
	confirmation), so its full GL activity is trusted:
	- Credits under voucher_type "Sales Invoice" are Excise recovered from
	  customers (a return/credit note posts a debit under the same voucher
	  type, netting it out automatically).
	- Any other voucher type (Journal Entry, Payment Entry, ...) is a Customs
	  payment; only its net debit is counted.
	"""
	gle = DocType("GL Entry")

	query = (
		frappe.qb.from_(gle)
		.select(
			gle.posting_date,
			gle.voucher_type,
			gle.voucher_no,
			gle.debit,
			gle.credit,
		)
		.where(gle.account == account)
		.where(gle.company == filters.company)
		.where(gle.is_cancelled == 0)
	)

	if filters.from_date:
		query = query.where(gle.posting_date >= filters.from_date)
	if filters.to_date:
		query = query.where(gle.posting_date <= filters.to_date)

	rows = query.orderby(gle.posting_date).run(as_dict=True)

	recovered_from_si = 0.0
	paid_to_customs = 0.0

	for row in rows:
		if row.voucher_type == "Sales Invoice":
			recovered_from_si += flt(row.credit) - flt(row.debit)
		else:
			paid_to_customs += flt(row.debit) - flt(row.credit)

	return flt(paid_to_customs, 2), flt(recovered_from_si, 2), rows


def get_expired_damaged_excise(filters):
	se = DocType("Stock Entry")
	sed = DocType("Stock Entry Detail")
	item = DocType("Item")

	query = (
		frappe.qb.from_(se)
		.join(sed)
		.on(sed.parent == se.name)
		.join(item)
		.on(item.name == sed.item_code)
		.select(
			se.posting_date,
			se.name.as_("voucher_no"),
			se.stock_entry_type,
			sed.item_code,
			sed.transfer_qty,
			item.custom_excise_rate,
		)
		.where(se.docstatus == 1)
		.where(se.company == filters.company)
		.where(se.stock_entry_type.isin(EXPIRED_DAMAGED_STOCK_ENTRY_TYPES))
		.where(item.custom_is_excisable == 1)
	)

	if filters.from_date:
		query = query.where(se.posting_date >= filters.from_date)
	if filters.to_date:
		query = query.where(se.posting_date <= filters.to_date)

	rows = query.orderby(se.posting_date).run(as_dict=True)

	total = 0.0
	for row in rows:
		row.amount = flt(flt(row.transfer_qty) * flt(row.custom_excise_rate), 2)
		total += row.amount

	return flt(total, 2), rows


def get_detail_rows(gl_rows, stock_rows):
	data = []

	for row in gl_rows:
		if row.voucher_type == "Sales Invoice":
			category = _("Recovered from Sales Invoices")
			amount = flt(row.credit) - flt(row.debit)
		else:
			category = _("Paid to Customs")
			amount = flt(row.debit) - flt(row.credit)

		data.append(
			{
				"posting_date": row.posting_date,
				"category": category,
				"voucher_type": row.voucher_type,
				"voucher_no": row.voucher_no,
				"amount": amount,
			}
		)

	for row in stock_rows:
		data.append(
			{
				"posting_date": row.posting_date,
				"category": _("Expired/Damaged Excise ({0})").format(row.stock_entry_type),
				"voucher_type": "Stock Entry",
				"voucher_no": row.voucher_no,
				"amount": -row.amount,
			}
		)

	data.sort(key=lambda r: r["posting_date"] or "")
	return data


def get_columns(show_details):
	if show_details:
		return [
			{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
			{"label": _("Category"), "fieldname": "category", "fieldtype": "Data", "width": 220},
			{"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 120},
			{
				"label": _("Voucher No"),
				"fieldname": "voucher_no",
				"fieldtype": "Dynamic Link",
				"options": "voucher_type",
				"width": 160,
			},
			{
				"label": _("Amount"),
				"fieldname": "amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 130,
			},
		]

	return [
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 200,
		},
		{
			"label": _("Paid to Customs"),
			"fieldname": "paid_to_customs",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"label": _("Recovered from Sales Invoices"),
			"fieldname": "recovered_from_si",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 250,
		},
		{
			"label": _("Expired/Damaged Excise"),
			"fieldname": "expired_damaged_excise",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 220,
		},
		{
			"label": _("Remaining Balance"),
			"fieldname": "remaining_balance",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 160,
		},
	]
