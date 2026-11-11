# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

ACTIVE = "Active"


class CommissionPlan(Document):
	def validate(self) -> None:
		self.validate_dates()
		if self.status == ACTIVE:
			self.validate_no_active_overlap()

	def validate_dates(self) -> None:
		if self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To cannot be before Valid From."))

	def validate_no_active_overlap(self) -> None:
		others = frappe.get_all(
			"Commission Plan",
			filters={"company": self.company, "status": ACTIVE, "name": ("!=", self.name)},
			fields=["name", "valid_from", "valid_to"],
		)
		for other in others:
			if self.overlaps(other.valid_from, other.valid_to):
				frappe.throw(
					_("Plan {0} is already Active for {1} from {2}. Close it or change the dates.").format(
						other.name, self.company, frappe.format(other.valid_from, {"fieldtype": "Date"})
					)
				)

	def overlaps(self, other_from: date, other_to: date | None) -> bool:
		starts_before_other_ends = other_to is None or getdate(self.valid_from) <= getdate(other_to)
		ends_after_other_starts = self.valid_to is None or getdate(self.valid_to) >= getdate(other_from)
		return starts_before_other_ends and ends_after_other_starts

	@staticmethod
	def get_active_plan(company: str, month: date) -> str | None:
		plans = frappe.get_all(
			"Commission Plan",
			filters={"company": company, "status": ACTIVE, "valid_from": ("<=", month)},
			or_filters=[["valid_to", "is", "not set"], ["valid_to", ">=", month]],
			pluck="name",
			order_by="valid_from desc",
			limit=1,
		)
		return plans[0] if plans else None
