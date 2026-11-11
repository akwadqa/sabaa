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
		self.validate_tiers()
		self.validate_shares()
		self.summary = self.get_summary()

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
