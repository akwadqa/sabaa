import unittest
from datetime import date

from sabaa.sabaa.commission.periods import PeriodMode, average_of_months, get_basis_months, month_end, month_start


class TestGetBasisMonths(unittest.TestCase):
	def test_monthly_is_the_payout_month(self):
		self.assertEqual(get_basis_months(PeriodMode.MONTHLY, date(2026, 5, 1)), [date(2026, 5, 1)])

	def test_rolling_covers_three_months(self):
		self.assertEqual(
			get_basis_months(PeriodMode.ROLLING, date(2026, 5, 1)),
			[date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1)],
		)

	def test_rolling_crosses_year_boundary(self):
		self.assertEqual(
			get_basis_months(PeriodMode.ROLLING, date(2026, 1, 1)),
			[date(2025, 11, 1), date(2025, 12, 1), date(2026, 1, 1)],
		)

	def test_quarterly_does_not_pay_outside_quarter_end(self):
		self.assertIsNone(get_basis_months(PeriodMode.QUARTERLY, date(2026, 5, 1)))

	def test_quarterly_pays_in_quarter_end_month_from_any_day(self):
		self.assertEqual(
			get_basis_months(PeriodMode.QUARTERLY, date(2026, 6, 15)),
			[date(2026, 4, 1), date(2026, 5, 1), date(2026, 6, 1)],
		)


class TestAverageOfMonths(unittest.TestCase):
	MONTHS = [date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1)]

	def average(self, *values):
		return average_of_months(dict(zip(self.MONTHS, values)), self.MONTHS)

	def test_average(self):
		self.assertEqual(self.average(60000, 90000, 120000), 90000)

	def test_missing_month_gives_none(self):
		self.assertIsNone(self.average(60000, None, 120000))

	def test_negative_month_is_averaged(self):
		self.assertEqual(self.average(-3000, 0, 3000), 0)

	def test_negative_average_is_kept(self):
		self.assertEqual(self.average(-6000, 0, 0), -2000)


class TestMonthBounds(unittest.TestCase):
	def test_month_start(self):
		self.assertEqual(month_start(date(2026, 2, 17)), date(2026, 2, 1))

	def test_month_end_handles_leap_year(self):
		self.assertEqual(month_end(date(2028, 2, 10)), date(2028, 2, 29))

	def test_accepts_date_strings(self):
		self.assertEqual(month_end("2026-04-03"), date(2026, 4, 30))
