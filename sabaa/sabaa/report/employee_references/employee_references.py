# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{
			"label": _("Reference"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Employee Reference",
			"width": 140,
		},
		{
			"label": _("Document"),
			"fieldname": "document",
			"fieldtype": "Select",
			"width": 120,
		},
		{
			"label": _("Reference No"),
			"fieldname": "reference_no",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Old Document No"),
			"fieldname": "old_document_no",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Place of Issue"),
			"fieldname": "place_of_issue",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Designation"),
			"fieldname": "designation",
			"fieldtype": "Link",
			"options": "Designation",
			"width": 120,
		},
		{
			"label": _("License Type"),
			"fieldname": "license_type",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Appointment Date"),
			"fieldname": "appointment_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Issue Date"),
			"fieldname": "issue_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Receiving Date"),
			"fieldname": "receiving_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Expiry Date"),
			"fieldname": "expiry_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Sponsorship"),
			"fieldname": "sponsorship",
			"fieldtype": "Link",
			"options": "Place of Work and Sponsorship",
			"width": 140,
		},
		{
			"label": _("Place of Work"),
			"fieldname": "place_of_work",
			"fieldtype": "Link",
			"options": "Place of Work and Sponsorship",
			"width": 140,
		},
		{
			"label": _("New Attachment"),
			"fieldname": "attachment",
			"fieldtype": "Attach",
			"width": 130,
		},
		{
			"label": _("Old Attachment"),
			"fieldname": "previous_attachment",
			"fieldtype": "Attach",
			"width": 130,
		},
		{
			"label": _("Previous Reference"),
			"fieldname": "previous_reference",
			"fieldtype": "Link",
			"options": "Employee Reference",
			"width": 140,
		},
		{
			"label": _("Is Current"),
			"fieldname": "is_current",
			"fieldtype": "Check",
			"width": 90,
		},
	]


def get_data(filters):
	reference_filters = {"employee": filters.get("employee")}

	if filters.get("document"):
		reference_filters["document"] = filters["document"]

	if filters.get("show_current_only"):
		reference_filters["is_current"] = 1

	return frappe.get_all(
		"Employee Reference",
		filters=reference_filters,
		fields=[
			"name",
			"document",
			"reference_no",
			"old_document_no",
			"place_of_issue",
			"designation",
			"license_type",
			"appointment_date",
			"issue_date",
			"receiving_date",
			"expiry_date",
			"sponsorship",
			"place_of_work",
			"attachment",
			"previous_attachment",
			"previous_reference",
			"is_current",
		],
		order_by="document asc, creation desc",
	)
