# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import unittest

import frappe

from sabaa.sabaa.commission.constants import LineStatus
from sabaa.sabaa.commission.distribution import split_pool
from sabaa.sabaa.commission.recipients import Member


def members(prefix: str, count: int) -> list[Member]:
	return [Member(f"{prefix}{n}", f"{prefix} {n}", None, None, "By designation") for n in range(1, count + 1)]


def share(name: str, percent: float, split: str = "Equal") -> frappe._dict:
	return frappe._dict(share_name=name, percent=percent, split=split)


class TestDistribution(unittest.TestCase):
	def test_drivers_and_workers_equal_split(self):
		allocations = split_pool(
			10000,
			[share("Drivers", 60), share("Workers", 40)],
			{"Drivers": members("D", 8), "Workers": members("W", 4)},
			{},
		)
		self.assertEqual([a.amount for a in allocations], [750] * 8 + [1000] * 4)
		self.assertTrue(all(a.status == LineStatus.READY for a in allocations))

	def test_rounding_remainder_goes_to_last_member(self):
		allocations = split_pool(1000, [share("All", 100)], {"All": members("M", 3)}, {})
		self.assertEqual([a.amount for a in allocations], [333.33, 333.33, 333.34])

	def test_share_without_members_is_not_assigned(self):
		allocations = split_pool(
			10000, [share("Drivers", 60), share("Workers", 40)], {"Drivers": members("D", 2)}, {}
		)
		unassigned = allocations[-1]
		self.assertEqual(
			(unassigned.member, unassigned.amount, unassigned.status), (None, 4000, LineStatus.NOT_ASSIGNED)
		)

	def test_split_by_assignment_percent(self):
		pool = members("H", 2)
		allocations = split_pool(
			1000, [share("Pool", 100, "By Assignment %")], {"Pool": pool}, {"H1": 70, "H2": 30}
		)
		self.assertEqual([a.amount for a in allocations], [700, 300])

	def test_percents_not_100_need_setup(self):
		pool = members("H", 2)
		allocations = split_pool(
			1000, [share("Pool", 100, "By Assignment %")], {"Pool": pool}, {"H1": 60, "H2": 35}
		)
		self.assertEqual({a.status for a in allocations}, {LineStatus.NEEDS_SETUP})
		self.assertEqual(allocations[0].note, "Shares total 95%")
