"""Monthly basis values for a rule: read each source once per range, fill early months from manual figures."""

from collections import defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.utils import flt, getdate

from sabaa.sabaa.commission import sources
from sabaa.sabaa.commission.periods import month_end
from sabaa.sabaa.doctype.commission_manual_figure.commission_manual_figure import get_manual_figures

COLLECTED_SALES = "Collected Sales"
NET_INVOICED_SALES = "Net Invoiced Sales"
COMPANY_SALES = "Company Sales"
DELIVERY_FEES = "Delivery Fees"
UNIT_COUNT = "Unit Count"
TENDER_COLLECTIONS = "Tender Collections"
PAIRED_BASIS = "Paired Basis"

MonthValues = dict[str | None, dict[date, float]]


def format_month(month: date) -> str:
	return getdate(month).strftime("%B %Y")


class BasisReader:
	"""Reads source rows for a plan. Results are cached per source and range, so each is read once per run."""

	def __init__(self, plan: frappe._dict, settings: frappe._dict, excluded_items: list[str]):
		self.plan = plan
		self.settings = settings
		self.excluded_items = excluded_items
		self._cache: dict[tuple, list] = {}

	def get_basis_rows(self, rule, from_date: date, to_date: date) -> list[sources.BasisRow]:
		if rule.basis == TENDER_COLLECTIONS:
			return self._cached(("tender", from_date, to_date), sources.get_tender_collections, self.plan.company, from_date, to_date)
		if rule.basis == UNIT_COUNT:
			groups = self.get_groups(rule)
			key = ("units", rule.name, from_date, to_date)
			return self._cached(key, sources.get_units, self.plan.company, groups, from_date, to_date, rule.unit_rates, self.settings.carton_uom)
		return [row for source in rule.basis_sources for row in self._read_measure(source, from_date, to_date)]

	def get_delivery_rows(self, rule, from_date: date, to_date: date) -> list[sources.DeliveryRow]:
		key = ("delivery", tuple(self.get_groups(rule)), from_date, to_date)
		return self._cached(key, sources.get_delivery_fees, self.plan.company, self.get_groups(rule), from_date, to_date, self.settings.delivery_charge_account)

	def get_groups(self, rule) -> list[str]:
		return sources.expand_customer_groups([row.customer_group for row in rule.basis_sources], self.plan.excluded_groups)

	def _read_measure(self, source, from_date: date, to_date: date) -> list[sources.BasisRow]:
		groups = sources.expand_customer_groups([source.customer_group], self.plan.excluded_groups)
		reader = sources.get_collected if source.measure == "Collected" else sources.get_invoiced
		key = (source.measure, tuple(groups), from_date, to_date)
		return self._cached(key, reader, self.plan.company, groups, from_date, to_date, self.excluded_items)

	def _cached(self, key: tuple, function, *args) -> list:
		if key not in self._cache:
			self._cache[key] = function(*args)
		return self._cache[key]


def build_month_values(
	rows: list[sources.BasisRow], months: list[date], erpnext_start: date, figures_rule: str, is_pooled: bool
) -> tuple[MonthValues, list[date], dict[tuple[str | None, str], float]]:
	"""Values per key and month, the manual months, and flagged amounts per (key, flag).

	Months before ERPNext come from manual figures. A key with no rows in an ERPNext month gets 0 for it;
	a manual month with no figure is left out.
	"""
	values: MonthValues = defaultdict(dict)
	flags: dict[tuple[str | None, str], float] = defaultdict(float)
	for row in rows:
		if row.month in months:
			key = None if is_pooled else row.key
			values[key][row.month] = values[key].get(row.month, 0) + row.amount
			if row.flag:
				flags[(key, row.flag)] += row.amount

	manual_months = [month for month in months if month < erpnext_start]
	figures = get_manual_figures(figures_rule, manual_months) if manual_months else {}
	for (month, key), amount in figures.items():
		values[None if is_pooled else key][month] = amount
	return values, manual_months, flags


def get_flag_notes(flags: dict[tuple[str | None, str], float], key: str | None) -> list[str]:
	"""Notes such as "12,300 attributed by customer" for one key."""
	from sabaa.sabaa.commission.tiers import format_number

	return [f"{format_number(flt(amount, 2))} {flag}" for (flag_key, flag), amount in sorted(flags.items(), key=lambda item: item[0][1]) if flag_key == key and amount]


def get_period_range(months: list[date]) -> tuple[date, date]:
	return months[0], month_end(months[-1])


def missing_month_note(months: list[date]) -> str:
	return _("{0} figure missing.").format(", ".join(format_month(month) for month in months))
