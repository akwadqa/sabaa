import unittest

from sabaa.sabaa.commission.tiers import Tier, calculate_tier, flat_rate, scale_tiers, validate_tiers

SALESPERSON = [
	Tier(70000, 200),
	Tier(84000, 367),
	Tier(105000, 1050),
	Tier(131250, 2362.5),
	Tier(157500, 3937.5, 3.5),
]
MODERN_POOL = [
	Tier(600000, 1800),
	Tier(700000, 1800, 1.25),
	Tier(900000, 2500, 1.75),
	Tier(1100000, 3500, 2),
]


class TestCalculateTier(unittest.TestCase):
	def test_below_first_tier(self):
		result = calculate_tier(69999.99, SALESPERSON)
		self.assertIsNone(result.tier_number)
		self.assertEqual(result.amount, 0)
		self.assertEqual(result.next_threshold, 70000)

	def test_threshold_is_inclusive(self):
		self.assertEqual(calculate_tier(84000, SALESPERSON).amount, 367)

	def test_fixed_step_keeps_previous_tier(self):
		self.assertEqual(calculate_tier(104999, SALESPERSON).amount, 367)

	def test_excess_on_last_tier(self):
		self.assertEqual(calculate_tier(167500, SALESPERSON).amount, 3937.5 + 350)

	def test_tier_number_and_gap(self):
		result = calculate_tier(120000, SALESPERSON)
		self.assertEqual((result.tier_number, result.tier_count, result.gap_to_next), (3, 5, 11250))

	def test_gap_is_none_at_last_tier(self):
		self.assertIsNone(calculate_tier(200000, SALESPERSON).gap_to_next)

	def test_negative_basis(self):
		result = calculate_tier(-500, SALESPERSON)
		self.assertIsNone(result.tier_number)
		self.assertEqual(result.amount, 0)

	def test_no_tiers(self):
		result = calculate_tier(1000, [])
		self.assertIsNone(result.tier_number)
		self.assertEqual((result.tier_count, result.amount, result.gap_to_next), (0, 0, None))

	def test_modern_pool_excess(self):
		self.assertEqual(calculate_tier(800000, MODERN_POOL).amount, 3050)


class TestScaleTiers(unittest.TestCase):
	def test_scale_targets_only(self):
		tiers = scale_tiers([Tier(800000, 5000)], 9, 8)
		self.assertEqual(tiers[0].threshold, 900000)
		self.assertEqual(tiers[0].fixed_amount, 5000)

	def test_scale_amounts_when_asked(self):
		self.assertEqual(scale_tiers([Tier(800000, 5000)], 9, 8, True)[0].fixed_amount, 5625)

	def test_zero_base_headcount_returns_tiers_unchanged(self):
		self.assertEqual(scale_tiers(SALESPERSON, 5, 0), SALESPERSON)


class TestFlatRate(unittest.TestCase):
	def test_flat_rate_tender(self):
		self.assertEqual(flat_rate(50000, 1.5), 750)


class TestValidateTiers(unittest.TestCase):
	def test_valid_tiers(self):
		self.assertEqual(validate_tiers(SALESPERSON), [])

	def test_order(self):
		self.assertEqual(
			validate_tiers([Tier(2, 1), Tier(1, 1)]),
			["Tier 2 must start above tier 1 (1 is not above 2)."],
		)

	def test_negative_values_and_percent_over_100(self):
		problems = validate_tiers([Tier(-1, -5, 101)])
		self.assertEqual(len(problems), 3)
