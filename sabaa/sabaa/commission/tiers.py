from dataclasses import dataclass, replace

from frappe.utils import flt


@dataclass(frozen=True)
class Tier:
	threshold: float
	fixed_amount: float
	excess_percent: float = 0


@dataclass(frozen=True)
class TierResult:
	tier_number: int | None
	tier_count: int
	threshold: float | None
	next_threshold: float | None
	fixed_part: float
	excess_part: float
	basis: float = 0

	@property
	def amount(self) -> float:
		return flt(self.fixed_part + self.excess_part, 2)

	@property
	def gap_to_next(self) -> float | None:
		if self.next_threshold is None:
			return None
		return flt(self.next_threshold - self.basis, 2)


def calculate_tier(basis: float, tiers: list[Tier]) -> TierResult:
	reached = [number for number, tier in enumerate(tiers, start=1) if tier.threshold <= basis]
	if not reached:
		next_threshold = tiers[0].threshold if tiers else None
		return TierResult(None, len(tiers), None, next_threshold, 0, 0, basis)

	number = reached[-1]
	tier = tiers[number - 1]
	next_threshold = tiers[number].threshold if number < len(tiers) else None
	excess = tier.excess_percent / 100 * (basis - tier.threshold)
	return TierResult(
		number,
		len(tiers),
		tier.threshold,
		next_threshold,
		tier.fixed_amount,
		flt(excess, 2),
		basis,
	)


def scale_tiers(
	tiers: list[Tier], actual_headcount: int, base_headcount: int, scale_amounts: bool = False
) -> list[Tier]:
	if base_headcount == 0:
		return tiers

	factor = actual_headcount / base_headcount
	return [
		replace(
			tier,
			threshold=flt(tier.threshold * factor, 2),
			fixed_amount=flt(tier.fixed_amount * factor, 2) if scale_amounts else tier.fixed_amount,
		)
		for tier in tiers
	]


def flat_rate(basis: float, percent: float) -> float:
	return flt(basis * percent / 100, 2)


def validate_tiers(tiers: list[Tier]) -> list[str]:
	problems = []
	for number, tier in enumerate(tiers, start=1):
		problems.extend(_validate_tier_values(number, tier))
		if number > 1 and tier.threshold <= tiers[number - 2].threshold:
			previous = tiers[number - 2].threshold
			problems.append(
				f"Tier {number} must start above tier {number - 1} "
				f"({tier.threshold:g} is not above {previous:g})."
			)
	return problems


def _validate_tier_values(number: int, tier: Tier) -> list[str]:
	problems = []
	if tier.threshold < 0:
		problems.append(f"Tier {number} threshold cannot be negative.")
	if tier.fixed_amount < 0:
		problems.append(f"Tier {number} fixed amount cannot be negative.")
	if tier.excess_percent < 0 or tier.excess_percent > 100:
		problems.append(f"Tier {number} excess percent must be between 0 and 100.")
	return problems
