"""The result type every commission calculation returns."""

from dataclasses import asdict, dataclass, field

from sabaa.sabaa.commission.constants import LineStatus


@dataclass
class CommissionLine:
	rule: str
	category: str
	role_label: str
	employee: str | None = None
	employee_name: str | None = None
	sales_person: str | None = None
	basis_label: str = ""
	month_values: dict[str, float | None] = field(default_factory=dict)
	basis_amount: float | None = None
	target: float | None = None
	tier_label: str | None = None
	next_target: float | None = None
	gap_to_next: float | None = None
	fixed_part: float = 0
	excess_part: float = 0
	share_name: str | None = None
	share_percent: float | None = None
	amount: float = 0
	status: LineStatus = LineStatus.READY
	notes: list[str] = field(default_factory=list)

	def as_dict(self) -> dict:
		values = asdict(self)
		values["status"] = str(self.status)
		return values
