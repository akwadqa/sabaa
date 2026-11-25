# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.report.customer_ledger_summary.customer_ledger_summary import (
	execute as customer_ledger_summary,
)
from frappe import _
from frappe.utils import flt

AMOUNT_FIELDS = (
	"opening_balance",
	"invoiced_amount",
	"paid_amount",
	"return_amount",
	"adjustment_amount",
	"closing_balance",
)


def execute(filters=None):
	return CustomerGroupLedgerSummary(filters).run()


class CustomerGroupLedgerSummary:
	"""Customer Ledger Summary totals shown as a Customer Group tree.

	Each group row holds its own customers plus all groups below it. The root group is not a row;
	customers directly on the root get their own top-level row."""

	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.parent_of = dict(
			frappe.get_all("Customer Group", fields=["name", "parent_customer_group"], as_list=True)
		)
		self.currency = frappe.get_cached_value("Company", self.filters.company, "default_currency")

	def run(self):
		native_columns, customer_rows = customer_ledger_summary(frappe._dict(self.filters))
		# Write-offs and discounts are taken out of Paid into one adj_<account> column per account.
		adjustment_fields = [column["fieldname"] for column in native_columns if column.get("is_adjustment")]

		group_totals = {}
		for customer_row in customer_rows:
			for group in self.get_row_groups(customer_row.customer_group):
				row = group_totals.setdefault(group, self.new_row(group))
				row.customer_count += 1
				row.adjustment_amount += sum(flt(customer_row.get(field)) for field in adjustment_fields)
				for field in AMOUNT_FIELDS:
					if field != "adjustment_amount":
						row[field] += flt(customer_row[field])

		data = self.get_tree_rows(group_totals)
		return self.get_columns(), data, None, None, self.get_summary(data)

	def new_row(self, group):
		return frappe._dict(
			customer_group=group,
			parent_customer_group=None,
			indent=0,
			customer_count=0,
			currency=self.currency,
			**dict.fromkeys(AMOUNT_FIELDS, 0),
		)

	def get_row_groups(self, group):
		"""The customer's group and its ancestors, without the root group (unless it is the group)."""
		groups = [group]
		while self.parent_of.get(groups[-1]):
			groups.append(self.parent_of[groups[-1]])

		if len(groups) > 1:
			groups.pop()
		return groups

	def get_tree_rows(self, group_totals):
		top_groups, children = [], {}
		for group in group_totals:
			parent = self.parent_of.get(group)
			# The root group's row holds only its own customers, so it never acts as a parent.
			if not parent or not self.parent_of.get(parent):
				top_groups.append(group)
			else:
				children.setdefault(parent, []).append(group)

		data = []

		def add_branch(group, indent):
			row = group_totals[group]
			row.indent = indent
			row.parent_customer_group = self.parent_of.get(group) if indent else None
			data.append(row)
			for child in sorted(children.get(group, [])):
				add_branch(child, indent + 1)

		for group in sorted(top_groups, key=lambda group: (group is None, group or "")):
			add_branch(group, 0)
		return data

	def get_summary(self, data):
		top_rows = [row for row in data if row.indent == 0]

		def card(label, field, indicator):
			return {
				"label": label,
				"value": sum(flt(row[field]) for row in top_rows),
				"datatype": "Currency",
				"currency": self.currency,
				"indicator": indicator,
			}

		return [
			card(_("Total Sales"), "invoiced_amount", "Blue"),
			card(_("Total Paid"), "paid_amount", "Green"),
			card(_("Total Return"), "return_amount", "Red"),
			card(_("Closing Balance"), "closing_balance", "Orange"),
		]

	def get_columns(self):
		def currency_column(label, fieldname):
			return {
				"label": label,
				"fieldname": fieldname,
				"fieldtype": "Currency",
				"options": "currency",
				"width": 140,
			}

		return [
			{
				"label": _("Customer Group"),
				"fieldname": "customer_group",
				"fieldtype": "Link",
				"options": "Customer Group",
				"width": 280,
			},
			{"label": _("Customers"), "fieldname": "customer_count", "fieldtype": "Int", "width": 100},
			currency_column(_("Opening Balance"), "opening_balance"),
			currency_column(_("Total Sales"), "invoiced_amount"),
			currency_column(_("Total Paid"), "paid_amount"),
			currency_column(_("Total Return"), "return_amount"),
			currency_column(_("Adjustments"), "adjustment_amount"),
			currency_column(_("Closing Balance"), "closing_balance"),
			{
				"label": _("Currency"),
				"fieldname": "currency",
				"fieldtype": "Link",
				"options": "Currency",
				"hidden": 1,
			},
		]
