"""Split a commission pool into shares, then among each share's members."""

from dataclasses import dataclass

import frappe
from frappe import _
from frappe.utils import flt

from sabaa.sabaa.commission.constants import LineStatus
from sabaa.sabaa.commission.recipients import Member
from sabaa.sabaa.commission.tiers import format_number

EQUAL = "Equal"


@dataclass
class Allocation:
	member: Member | None
	share_name: str | None
	share_percent: float
	amount: float
	status: LineStatus
	note: str | None = None


def split_pool(
	amount: float,
	shares: list[frappe._dict],
	members_by_share: dict[str, list[Member]],
	percents_by_employee: dict[str, float],
) -> list[Allocation]:
	allocations = []
	for share in shares:
		share_amount = flt(amount * flt(share.percent) / 100, 2)
		members = members_by_share.get(share.share_name) or []
		if not members:
			allocations.append(
				Allocation(None, share.share_name, flt(share.percent), share_amount, LineStatus.NOT_ASSIGNED)
			)
		elif share.split == EQUAL:
			allocations.extend(split_equally(share_amount, share, members))
		else:
			allocations.extend(split_by_percent(share_amount, share, members, percents_by_employee))
	return allocations


def split_equally(amount: float, share: frappe._dict, members: list[Member]) -> list[Allocation]:
	each = flt(amount / len(members), 2)
	amounts = [each] * (len(members) - 1)
	amounts.append(flt(amount - sum(amounts), 2))
	percent = flt(share.percent) / len(members)
	return [
		Allocation(member, share.share_name, percent, member_amount, LineStatus.READY)
		for member, member_amount in zip(members, amounts)
	]


def split_by_percent(
	amount: float, share: frappe._dict, members: list[Member], percents_by_employee: dict[str, float]
) -> list[Allocation]:
	percents = [flt(percents_by_employee.get(member.employee)) for member in members]
	total = sum(percents)
	status, note = LineStatus.READY, None
	if flt(total, 2) != 100:
		status, note = LineStatus.NEEDS_SETUP, _("Shares total {0}%").format(format_number(total))

	amounts = [flt(amount * percent / 100, 2) for percent in percents]
	if status == LineStatus.READY:
		amounts[-1] = flt(amount - sum(amounts[:-1]), 2)
	return [
		Allocation(member, share.share_name, flt(share.percent) * percent / 100, member_amount, status, note)
		for member, percent, member_amount in zip(members, percents, amounts)
	]
