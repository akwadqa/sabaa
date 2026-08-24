# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.utils import getdate, nowdate, date_diff
from pypika import functions as fn

def execute(filters=None):
	filters = frappe._dict(filters or {})

	#Handle Dates
	filters.from_date = getdate(filters.from_date or nowdate())
	filters.to_date = getdate(filters.to_date or nowdate())
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	columns = get_columns(filters)
	data = get_data(filters)
	for row in data:
		row["remaining_balance"] = row["credit_sales"] + row["outstanding_collection"]

	return columns, data



def get_columns(filters):
	columns = []
	if filters.get("group_by_sales_provider"):
		columns.append({
			"label": _("Sales Provider"),
			"fieldtype": "Link",
			"fieldname": "sales_provider",
			"options": "Sales Person",
			"width": 200
		})

	columns.append({
		"label": _("Customer Group"),
		"fieldtype": "Link",
		"fieldname": "customer_group",
		"options": "Customer Group",
		"width": 200
	})
	
	if not filters.get("group_by_customer_group"):
		columns.append({
				"label": _("Customer"),
				"fieldtype": "Link",
				"fieldname": "customer",
				"options": "Customer",
				"width": 280
		})
	
	columns.extend([
		{
			"label": _("Total Sales Invoices"),
			"fieldtype": "Currency",
			"fieldname": "total_invoices",
			"width": 150
		},
		{
			"label": _("Paid Sales Collection"),
			"fieldtype": "Currency",
			"fieldname": "paid_collection",
			"width": 150
		},
		{
			"label": _("Outstanding Sales Collection"),
			"fieldtype": "Currency",
			"fieldname": "outstanding_collection",
			"width": 150
		},
		{
			"label": _("Credit Sales"),
			"fieldtype": "Currency",
			"fieldname": "credit_sales",
			"width": 150
		},
		{
			"label": _("Remaining Balance"),
			"fieldtype": "Currency",
			"fieldname": "remaining_balance",
			"width": 150
		},
		{
			"label": _("Sales Returns"),
			"fieldtype": "Currency",
			"fieldname": "sales_returns",
			"width": 150
		},
	])

	return columns

def get_data(filters):
	invoices = fetch_invoices(filters)

	invoice_names = [invoice.invoice for invoice in invoices]
	payments = fetch_invoice_linked_payments(invoice_names, filters)

	report_date = nowdate()
	provider_map = get_sales_provider_map() if filters.get("group_by_sales_provider") else {}

	totals = {}
	for invoice in invoices:
		row_template = {"customer_group": invoice.customer_group}

		if filters.get("group_by_sales_provider"):
			row_template["sales_provider"] = provider_map.get(invoice.sales_person)

		if not filters.get("group_by_customer_group"):
			row_template["customer"] = invoice.customer_name

		key = tuple(row_template.values())
		row = totals.setdefault(
			key,
			frappe._dict(
				{
					**row_template,
					"total_invoices": 0,
					"paid_collection": 0,
					"outstanding_collection": 0,
					"credit_sales": 0,
					"sales_returns": 0,
					"remaining_balance": 0,
				}
			),
		)

		if invoice.is_return:
			row.sales_returns += abs(invoice.grand_total)
		else:
			row.total_invoices += invoice.grand_total
			row.paid_collection += payments.get(invoice.invoice, 0)
			#row.paid_collection += invoice.grand_total - invoice.outstanding_amount

			if date_diff(report_date, invoice.due_date) <= 0:
				row.credit_sales += invoice.outstanding_amount
			else:
				row.outstanding_collection += invoice.outstanding_amount

	return list(totals.values())


def get_sales_provider_map():
	sales_persons = frappe.get_all("Sales Person", fields=["name", "parent_sales_person"])
	parent_by_name = {sp.name: sp.parent_sales_person for sp in sales_persons}

	cache = {}

	def resolve(name):
		if name not in cache:
			provider = name
			parent = parent_by_name.get(name)
			while parent:
				provider = parent
				parent = parent_by_name.get(parent)
			cache[name] = provider
		return cache[name]

	return {name: resolve(name) for name in parent_by_name}

def fetch_invoices(filters):
	invoice = qb.DocType("Sales Invoice")
	team = qb.DocType("Sales Team")
	customer = qb.DocType("Customer")

	invoices_query = (
		qb.from_(invoice)
		.left_join(team)
		.on(invoice.name == team.parent)
		.left_join(customer)
		.on(invoice.customer == customer.name)
		.select(
			invoice.name.as_("invoice"),
			invoice.is_return,
			invoice.due_date,
			invoice.customer,
			invoice.grand_total,
			invoice.outstanding_amount,
			customer.customer_group,
			customer.customer_name,
			team.sales_person,
		)
		.where(invoice.docstatus == 1)
		.where(invoice.posting_date >= filters.from_date)
		.where(invoice.posting_date <= filters.to_date)
	)

	if filters.get("customer", None):
		invoices_query = invoices_query.where(invoice.customer.isin(filters.get("customer")))
	if filters.get("customer_group", None):
		invoices_query = invoices_query.where(customer.customer_group == filters.get("customer_group"))
	if filters.get("sales_person", None):
		invoices_query = invoices_query.where(filters.get("sales_person").isin(team.sales_person))
	

	return invoices_query.run(as_dict=True)

def fetch_invoice_linked_payments(invoices, filters):
	company = filters.get("company")
	debit_accounts = frappe.get_all("Sales Collection Account", {"parent": company}, pluck="sales_collection_account")
	if not debit_accounts:
		frappe.throw("Please specify accounts for Paid Collections")
	filters["debit_accounts"] = debit_accounts

	payments = fetch_invoice_linked_payment_entries(invoices, filters)
	je_payments = fetch_invoice_linked_journal_entries(invoices, filters)

	for invoice, amount in je_payments.items():
		payments[invoice] = payments.get(invoice, 0) + amount
	return payments

def fetch_invoice_linked_payment_entries(invoices, filters):
	pe = qb.DocType("Payment Entry")
	per = qb.DocType("Payment Entry Reference")

	query = (
		qb.from_(per)
		.join(pe).on(per.parent == pe.name)
		.select(
			per.reference_name.as_("invoice"),
			fn.Sum(per.allocated_amount).as_("paid_amount"),
		)
		.where(pe.docstatus == 1)
		.where(pe.payment_type == "Receive")
		.where(per.reference_doctype == "Sales Invoice")
		.where(pe.paid_to.isin(filters.get("debit_accounts", [])))
		.where(per.reference_name.isin(invoices))
		.groupby(per.reference_name)
	)
	return {row.invoice: row.paid_amount for row in query.run(as_dict=True)}

def fetch_invoice_linked_journal_entries(invoices, filters):
	je = qb.DocType("Journal Entry")
	jea = qb.DocType("Journal Entry Account")
	jea_debit = qb.DocType("Journal Entry Account").as_("jea_debit")

	qualifying_je = (
		qb.from_(jea_debit)
		.select(jea_debit.parent)
		.distinct()
		.where(jea_debit.account.isin(filters.get("debit_accounts", [])))
		.where(jea_debit.debit_in_account_currency > 0)
	)

	query = (
		qb.from_(jea)
		.join(je).on(jea.parent == je.name)
		.select(
			jea.reference_name.as_("invoice"),
			fn.Sum(jea.credit_in_account_currency).as_("paid_amount"),
		)
		.where(je.docstatus == 1)
		.where(jea.reference_type == "Sales Invoice")
		.where(jea.reference_name.isin(invoices))
		.where(jea.parent.isin(qualifying_je))
		.groupby(jea.reference_name)
	)
	return {row.invoice: row.paid_amount for row in query.run(as_dict=True)}

