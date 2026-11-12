# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from sabaa.sabaa.commission.tiers import Tier, format_number, validate_tiers

TIERED = "Tiered"
FLAT_RATE = "Flat Rate"
POOL = "Pool"
FULL_SHARE_PERCENT = 100


class CommissionRule(Document):
	def validate(self) -> None:
		self.validate_not_locked()
		self.validate_tiers()
		self.validate_shares()
		self.summary = self.get_summary()

	def validate_not_locked(self) -> None:
		before = self.get_doc_before_save()
		if before and get_calculation_fingerprint(before) == get_calculation_fingerprint(self):
			return
		self.throw_if_plan_locked()

	def on_trash(self) -> None:
		self.throw_if_plan_locked()

	def throw_if_plan_locked(self) -> None:
		from sabaa.sabaa.doctype.commission_run.commission_run import get_locked_runs

		runs = get_locked_runs(self.plan)
		if runs:
			frappe.throw(_("Run {0} is approved. Copy the plan to change the rules.").format(runs[0].name))

	def validate_tiers(self) -> None:
		if self.tier_method != TIERED:
			return
		if not self.tiers:
			if not self.is_waiting_for_business:
				frappe.throw(_("Add at least one tier, or tick Waiting for business input."))
			return
		problems = validate_tiers(self.get_tiers())
		if problems:
			frappe.throw("<br>".join(problems))

	def validate_shares(self) -> None:
		if self.recipient_source != POOL:
			return
		if not self.shares:
			if not self.is_waiting_for_business:
				frappe.throw(_("Add at least one share for this pool, or tick Waiting for business input."))
			return
		total = sum(share.percent or 0 for share in self.shares)
		if round(total, 6) != FULL_SHARE_PERCENT:
			frappe.throw(_("Shares total {0}%. They must total 100%.").format(format_number(total)))

	def get_tiers(self) -> list[Tier]:
		return [
			Tier(row.threshold or 0, row.fixed_amount or 0, row.excess_percent or 0) for row in self.tiers
		]

	def get_summary(self) -> str:
		parts = [self.get_method_summary(), self.period_mode, self.basis]
		return " · ".join(part for part in parts if part)

	def get_method_summary(self) -> str:
		if self.tier_method == TIERED:
			count = len(self.tiers)
			return f"{count} tier{'' if count == 1 else 's'}"
		if self.tier_method == FLAT_RATE:
			return f"{format_number(self.flat_rate_percent or 0)}% flat rate"
		count = len(self.unit_rates)
		return f"{count} unit rate{'' if count == 1 else 's'}"


LOCKED_FIELDS = (
	"basis", "period_mode", "payout_multiplier", "tier_method", "flat_rate_percent", "recipient_source",
	"attribute_by", "headcount_base", "headcount_share", "scale_amounts", "bonus_after_count", "bonus_per_unit",
	"team_group", "paired_rule", "is_waiting_for_business",
)
LOCKED_TABLES = {
	"tiers": ("threshold", "fixed_amount", "excess_percent"),
	"shares": ("share_name", "percent", "designation", "department", "split"),
	"basis_sources": ("customer_group", "measure"),
	"unit_rates": ("item", "uom", "amount_per_unit"),
	"member_designations": ("designation",),
}


def get_calculation_fingerprint(doc) -> tuple:
	"""The values that change what an approved run would pay."""
	fields = tuple(doc.get(field) for field in LOCKED_FIELDS)
	tables = tuple(
		tuple(tuple(row.get(column) for column in columns) for row in doc.get(table) or [])
		for table, columns in LOCKED_TABLES.items()
	)
	return fields + tables
