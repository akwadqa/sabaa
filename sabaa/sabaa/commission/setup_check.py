"""Plain-language setup problems for a plan and month, each with a link to where it is fixed."""

from dataclasses import asdict, dataclass, field
from datetime import date

import frappe
from frappe import _


@dataclass(frozen=True)
class SetupProblem:
	rule: str | None
	message: str
	fix: dict = field(default_factory=dict, hash=False, compare=False)

	def as_dict(self) -> dict:
		return asdict(self)


def check_setup(plan: str, month: date, reader=None) -> list[SetupProblem]:
	"""Problems found while calculating the month, plus settings the engine needs."""
	from sabaa.sabaa.commission.engine import CommissionEngine

	engine = CommissionEngine(plan, month, reader)
	engine.calculate()
	problems = get_settings_problems(engine) + engine.problems

	unique: dict[tuple, SetupProblem] = {}
	for problem in problems:
		unique.setdefault((problem.rule, problem.message), problem)
	return list(unique.values())


def get_settings_problems(engine) -> list[SetupProblem]:
	problems = []
	bases = {rule.basis for rule in engine.rules}
	if "Delivery Fees" in bases and not engine.settings.delivery_charge_account:
		problems.append(
			SetupProblem(
				None,
				_("Commission Settings: set the delivery charge account."),
				{"doctype": "Commission Settings", "name": "Commission Settings"},
			)
		)
	if not frappe.get_all("Sales Collection Account", filters={"parent": engine.plan.company, "parenttype": "Company"}, limit=1):
		problems.append(
			SetupProblem(
				None,
				_("Company {0} has no sales collection accounts.").format(engine.plan.company),
				{"doctype": "Company", "name": engine.plan.company},
			)
		)
	return problems
