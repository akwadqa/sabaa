# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe

COMPANY = "Saba Trading Group"


def make_employee(name: str, designation: str | None = None, department: str | None = None, **fields) -> str:
	values = {
		"doctype": "Employee",
		"first_name": name,
		"gender": "Male",
		"date_of_birth": "1990-01-01",
		"date_of_joining": "2020-01-01",
		"status": "Active",
		"company": COMPANY,
		"designation": designation,
		"department": department,
	}
	values.update(fields)
	return frappe.get_doc(values).insert().name


def make_sales_person(
	name: str, employee: str | None = None, parent: str = "Sales Team", is_group: int = 0
) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Sales Person",
				"sales_person_name": name,
				"parent_sales_person": parent,
				"is_group": is_group,
				"employee": employee,
			}
		)
		.insert()
		.name
	)


def make_plan(plan_name: str, valid_from: str, valid_to: str | None, status: str = "Active"):
	return frappe.get_doc(
		{
			"doctype": "Commission Plan",
			"plan_name": plan_name,
			"company": COMPANY,
			"valid_from": valid_from,
			"valid_to": valid_to,
			"status": status,
		}
	).insert()


def make_customer_group(name: str, parent: str = "All Customer Groups", is_group: int = 0) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Customer Group",
				"customer_group_name": name,
				"parent_customer_group": parent,
				"is_group": is_group,
			}
		)
		.insert()
		.name
	)


def make_customer(name: str, customer_group: str) -> str:
	return (
		frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_group": customer_group})
		.insert()
		.name
	)


def make_service_item(item_code: str) -> str:
	"""Returns the Item name, which the site's naming series makes differ from `item_code`."""
	return (
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_group": "Canned Food",
				"stock_uom": "Nos",
				"is_stock_item": 0,
			}
		)
		.insert()
		.name
	)


def make_account(account_name: str, is_collection: bool) -> str:
	"""A balance-sheet account under the company's cash group, optionally listed as a collection account."""
	parent = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_name": "Cash In Hand", "is_group": 1}
	)
	account = (
		frappe.get_doc(
			{"doctype": "Account", "account_name": account_name, "parent_account": parent, "company": COMPANY}
		)
		.insert()
		.name
	)
	if is_collection:
		company = frappe.get_doc("Company", COMPANY)
		company.append("sales_collection_accounts", {"sales_collection_account": account}).db_insert()
	return account


def make_sales_invoice(
	customer: str,
	sales_person: str | None,
	posting_date: str,
	items: list[tuple[str, float]],
	is_return: int = 0,
	pos_account: str | None = None,
) -> str:
	"""Submit an invoice; `items` is (item_code, net amount) with qty 1 (-1 on returns).

	With `pos_account` the invoice is a POS invoice paid in full in cash to that account.
	"""
	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": COMPANY,
			"customer": customer,
			"posting_date": posting_date,
			"set_posting_time": 1,
			"due_date": posting_date,
			"is_return": is_return,
			"items": [
				{"item_code": item_code, "qty": -1 if is_return else 1, "rate": amount}
				for item_code, amount in items
			],
		}
	)
	if sales_person:
		invoice.append("sales_team", {"sales_person": sales_person, "allocated_percentage": 100})
	if pos_account:
		invoice.is_pos = 1
		invoice.pos_profile = frappe.db.get_value("POS Profile", {"company": COMPANY})
		paid = sum(amount for _item_code, amount in items)
		invoice.append("payments", {"mode_of_payment": "Cash", "account": pos_account, "amount": paid})
	return invoice.insert().submit().name


def make_payment_entry(
	customer: str, posting_date: str, amount: float, paid_to: str, invoice: str | None = None
) -> str:
	payment = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"company": COMPANY,
			"posting_date": posting_date,
			"party_type": "Customer",
			"party": customer,
			"paid_from": frappe.get_cached_value("Company", COMPANY, "default_receivable_account"),
			"paid_to": paid_to,
			"paid_amount": amount,
			"received_amount": amount,
			"reference_no": "TEST",
			"reference_date": posting_date,
		}
	)
	if invoice:
		payment.append(
			"references",
			{"reference_doctype": "Sales Invoice", "reference_name": invoice, "allocated_amount": amount},
		)
	return payment.insert().submit().name


def make_journal_entry(
	customer: str,
	posting_date: str,
	amount: float,
	account: str,
	reference: tuple[str, str] | None = None,
	is_opening: str = "No",
) -> str:
	"""Credit the customer by `amount` against `account`; a negative amount debits the customer.

	`reference` is (doctype, name) the customer row is allocated to.
	"""
	reference_type, reference_name = reference or (None, None)
	customer_row = {
		"account": frappe.get_cached_value("Company", COMPANY, "default_receivable_account"),
		"party_type": "Customer",
		"party": customer,
		"credit_in_account_currency": max(amount, 0),
		"debit_in_account_currency": max(-amount, 0),
		"reference_type": reference_type,
		"reference_name": reference_name,
	}
	other_row = {
		"account": account,
		"debit_in_account_currency": max(amount, 0),
		"credit_in_account_currency": max(-amount, 0),
	}
	return (
		frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Opening Entry" if is_opening == "Yes" else "Journal Entry",
				"is_opening": is_opening,
				"company": COMPANY,
				"posting_date": posting_date,
				"accounts": [customer_row, other_row],
			}
		)
		.insert()
		.submit()
		.name
	)
