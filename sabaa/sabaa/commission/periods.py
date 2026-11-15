from datetime import date
from enum import StrEnum

from frappe.utils import add_months, get_first_day, get_last_day, getdate

MONTHS_IN_QUARTER = 3


class PeriodMode(StrEnum):
	MONTHLY = "Monthly"
	QUARTERLY = "Quarterly Average"
	ROLLING = "Rolling 3-Month Average"


def month_start(value: date | str) -> date:
	return get_first_day(getdate(value))


def month_end(value: date | str) -> date:
	return get_last_day(getdate(value))


def get_basis_months(mode: PeriodMode, payout_month: date | str) -> list[date] | None:
	"""First-of-month dates the rule averages; None when the rule does not pay in this month."""
	first = month_start(payout_month)
	if mode == PeriodMode.MONTHLY:
		return [first]
	if mode == PeriodMode.QUARTERLY and first.month % MONTHS_IN_QUARTER:
		return None
	return [add_months(first, -offset) for offset in reversed(range(MONTHS_IN_QUARTER))]


def average_of_months(values: dict[date, float | None], months: list[date]) -> float | None:
	"""None if any month is None. Months with no rows must be passed as 0.0 by the caller."""
	month_values = [values[month] for month in months]
	if any(value is None for value in month_values):
		return None
	return sum(month_values) / len(month_values)
