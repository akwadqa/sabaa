# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull

ASSISTANT_OF = "Assistant Of"
POOL_SHARE_PERCENT = "Pool Share %"
SHARE_MEMBER = "Share Member"
LOCKED_VALUE_FIELDS = ("rule", "employee", "assignment_type", "target_sales_person", "share_name", "percent")


class CommissionAssignment(Document):
	def validate(self) -> None:
		self.validate_dates()
		self.validate_not_locked()
		self.validate_type_fields()
		self.validate_no_overlap()

	def validate_dates(self) -> None:
		if self.to_date and self.to_date < self.from_date:
			frappe.throw(_("To Date cannot be before From Date."))

	def validate_not_locked(self) -> None:
		"""Refuse a change that alters what an approved month paid; ending a row after it is allowed."""
		from sabaa.sabaa.doctype.commission_run.commission_run import get_covered_locked_runs, throw_locked

		plan = frappe.db.get_value("Commission Rule", self.rule, "plan")
		before = self.get_doc_before_save()
		new = get_covered_locked_runs(plan, self.from_date, self.to_date)
		old = get_covered_locked_runs(plan, before.from_date, before.to_date) if before else set()
		changed = (old ^ new) or (before and (old & new) and self.has_locked_value_change(before))
		if changed:
			run_name, month = sorted((old ^ new) or (old & new), key=lambda run: run[1])[0]
			throw_locked(run_name, month)

	def has_locked_value_change(self, before) -> bool:
		# Empty values read back as None or 0 depending on the path; both mean "not set".
		return any((before.get(field) or None) != (self.get(field) or None) for field in LOCKED_VALUE_FIELDS)

	def on_trash(self) -> None:
		from sabaa.sabaa.doctype.commission_run.commission_run import get_covered_locked_runs, throw_locked

		plan = frappe.db.get_value("Commission Rule", self.rule, "plan")
		covered = sorted(get_covered_locked_runs(plan, self.from_date, self.to_date), key=lambda run: run[1])
		if covered:
			throw_locked(*covered[0])

	def validate_no_overlap(self) -> None:
		"""Two open rows of one kind for one person would pay them twice."""
		assignment = DocType("Commission Assignment")
		query = (
			frappe.qb.from_(assignment)
			.select(assignment.name)
			.where(
				(assignment.rule == self.rule)
				& (assignment.employee == self.employee)
				& (assignment.assignment_type == self.assignment_type)
				& (assignment.name != (self.name or ""))
				& (assignment.from_date <= (self.to_date or date.max))
				& (IfNull(assignment.to_date, date.max) >= self.from_date)
			)
		)
		if self.assignment_type == SHARE_MEMBER:
			query = query.where(assignment.share_name == self.share_name)
		other = query.run(pluck=True)
		if other:
			frappe.throw(
				_("{0} already has an overlapping {1} row on this rule: {2}.").format(self.employee, self.assignment_type, other[0])
			)

	def validate_type_fields(self) -> None:
		if self.assignment_type == ASSISTANT_OF and not self.target_sales_person:
			frappe.throw(_("Choose the salesman this assistant works with."))
		if self.assignment_type == POOL_SHARE_PERCENT and not self.percent:
			frappe.throw(_("Enter the percent this person receives from the pool."))
		if self.assignment_type == SHARE_MEMBER:
			self.validate_share_name()

	def validate_share_name(self) -> None:
		share_names = frappe.get_all("Commission Share", filters={"parent": self.rule}, order_by="idx", pluck="share_name")
		if self.share_name not in share_names:
			frappe.throw(
				_("{0} is not a share of rule {1}. Choose one of: {2}.").format(
					self.share_name or "-", self.rule, ", ".join(share_names) or "-"
				)
			)


def get_assignments(
	rule: str, start: date, end: date, assignment_type: str | None = None
) -> list[frappe._dict]:
	"""Rows of the rule whose date range overlaps start..end (an empty to_date has no end)."""
	assignment = DocType("Commission Assignment")
	query = (
		frappe.qb.from_(assignment)
		.select("*")
		.where(assignment.rule == rule)
		.where(assignment.from_date <= end)
		.where(IfNull(assignment.to_date, date.max) >= start)
		.orderby(assignment.from_date)
	)
	if assignment_type:
		query = query.where(assignment.assignment_type == assignment_type)
	return query.run(as_dict=True)
