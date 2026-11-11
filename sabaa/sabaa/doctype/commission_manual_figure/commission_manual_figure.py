# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull
from frappe.utils import formatdate, getdate

from sabaa.sabaa.commission.periods import month_start


class CommissionManualFigure(Document):
	def validate(self) -> None:
		self.month = month_start(self.month)
		self.validate_plan()
		self.validate_month_before_erpnext()
		self.validate_is_unique()

	def validate_plan(self) -> None:
		rule_plan = frappe.db.get_value("Commission Rule", self.rule, "plan")
		if self.plan and self.plan != rule_plan:
			frappe.throw(_("Rule {0} belongs to plan {1}.").format(self.rule, rule_plan))
		self.plan = rule_plan

	def validate_month_before_erpnext(self) -> None:
		configured = frappe.db.get_single_value("Commission Settings", "erpnext_start_date")
		start_date = getdate(configured)
		if start_date == date.min:  # an unset Single date reads back as 0001-01-01
			frappe.throw(_("Set the ERPNext Start Date in Commission Settings."))
		if self.month >= start_date:
			frappe.throw(
				_("{0} is in ERPNext. Manual figures are only for months before {1}.").format(
					formatdate(self.month, "MMMM yyyy"), start_date.isoformat()
				)
			)

	def validate_is_unique(self) -> None:
		figure = DocType("Commission Manual Figure")
		duplicate = (
			frappe.qb.from_(figure)
			.select(figure.name)
			.where(figure.rule == self.rule)
			.where(figure.month == self.month)
			.where(IfNull(figure.sales_person, "") == (self.sales_person or ""))
			.where(figure.name != self.name)
			.run()
		)
		if duplicate:
			frappe.throw(
				_("A figure for {0}, {1}, {2} already exists: {3}.").format(
					self.rule,
					formatdate(self.month, "MMMM yyyy"),
					self.sales_person or _("whole rule"),
					duplicate[0][0],
				)
			)


def get_manual_figures(rule: str, months: list[date]) -> dict[tuple[date, str | None], float]:
	if not months:
		return {}
	rows = frappe.get_all(
		"Commission Manual Figure",
		filters={"rule": rule, "month": ["in", months]},
		fields=["month", "sales_person", "amount"],
	)
	return {(row.month, row.sales_person or None): row.amount or 0 for row in rows}
