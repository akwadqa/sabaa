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
