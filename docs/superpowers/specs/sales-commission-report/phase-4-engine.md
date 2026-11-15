# Sales Commission Report – Phase 4: Recipients and engine

> Read `plan-overview.md` first: it holds the global constraints, review focus and file map that apply to every task here.

### Task 8: Recipients and distribution

**Files:** Create `sabaa/sabaa/commission/recipients.py`, `sabaa/sabaa/commission/distribution.py`, tests `test_recipients.py` (integration), `test_distribution.py` (pure).

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Member: employee: str | None; employee_name: str; sales_person: str | None; designation: str | None; source: str` — `source` in `"From HR tree"`, `"By designation"`, `"Added by hand"`.
  - `get_tree_members(group: str, designations: list[str], start: date, end: date) -> list[Member]` — enabled leaf Sales Persons under the group; eligible employee = status Active, or `relieving_date >= start`; a leaf with no employee is returned with `employee=None` (the engine marks it Needs setup).
  - `get_group_supervisors(group: str) -> dict[str, str]` — sub-group name → `Sales Person.employee` of each group node under (and including) `group` that has an employee.
  - `get_designation_members(designation: str, department: str | None, start, end) -> list[Member]`
  - `apply_overrides(members: list[Member], rule: str, start, end) -> list[Member]` — Exclude removes, Include adds with source "Added by hand".
  - `distribution.py`: `@dataclass class Allocation: member: Member | None; share_name: str | None; share_percent: float; amount: float; status: LineStatus; note: str | None`; `split_pool(amount: float, shares: list[frappe._dict], members_by_share: dict[str, list[Member]], percents_by_employee: dict[str, float]) -> list[Allocation]` — Equal split or By Assignment %; a share with no members → one `Allocation(member=None, status=NOT_ASSIGNED)`; percents not totalling 100 inside a share → `NEEDS_SETUP` lines with note "Shares total 95%". Rounding remainder goes to the last member so the sum equals `amount`.

- [ ] **Step 1: Failing tests:**
  - pure: `split_pool(10000, [Drivers 60 Equal, Workers 40 Equal], 8 drivers, 4 workers)` → each driver 750, each worker 1000; 1,000 across 3 equal → 333.33, 333.33, 333.34; empty Workers → a 4,000 NOT_ASSIGNED allocation.
  - integration: Sales Head leaf in the cash group is filtered out by designations [Salesman]; leaf without employee returned with `employee=None` (Review Focus 3); employee relieved 2026-05-10 is eligible for May, not June; Exclude assignment removes the person only within its dates.
- [ ] **Step 2–4:** FAIL → implement → PASS
- [ ] **Step 5: Commit** — `feat(commission): resolve recipients and split pools`

---

### Task 9: Engine, setup check and API

**Files:** Create `sabaa/sabaa/commission/engine.py`, `sabaa/sabaa/commission/setup_check.py`, `sabaa/sabaa/commission/api.py`; tests `test_engine.py`, `test_setup_check.py`.

**Interfaces:**
- Consumes everything from Tasks 2–8.
- Produces:
  - `@dataclass class CommissionLine: rule: str; category: str; role_label: str; employee: str | None; employee_name: str | None; sales_person: str | None; basis_label: str; month_values: dict[str, float | None]; basis_amount: float | None; target: float | None; tier_label: str | None; next_target: float | None; gap_to_next: float | None; fixed_part: float; excess_part: float; share_name: str | None; share_percent: float | None; amount: float; status: LineStatus; notes: list[str]` with `as_dict()`.
  - `class CommissionEngine: __init__(self, plan: str, month: date)`, `calculate(self) -> list[CommissionLine]`, `calculate_rule(self, rule_name: str) -> list[CommissionLine]`. Each source is read once per engine run for the widest month range any rule needs, then filtered in memory. Rules with `is_waiting_for_business` give one line per expected recipient (or one pool line) with status WAITING and `notes=[status_note]`. Months before `erpnext_start_date` come from Manual Figures; a missing one → MISSING_DATA. Quarterly rules not paying this month return no lines. `payout_multiplier` multiplies the final amount. Cashier Assistant: basis and scaled tiers of the paired salesman, assistant's own amounts. Supervisor: sum of the members of each sub-group returned by `get_group_supervisors`; headcount = members counted. Logistics: headcount = members of share `headcount_share`. Company Sales: the sum over `basis_sources` rows, each read with its own measure (`get_collected` or `get_invoiced`), one total with `key=None`. Smile24 drivers: per driver `fee_amount × flat_rate_percent/100 + max(0, free_order_count − bonus_after_count) × bonus_per_unit`.
  - `@dataclass class SetupProblem: rule: str | None; message: str; fix: dict` — `fix` is `{"doctype": ..., "name": ...}` or `{"action": "people" | "manual_figures", "rule": ...}`.
  - `check_setup(plan: str, month: date) -> list[SetupProblem]` — messages (exact copy): `"Sales Person {0} has no employee."`, `"Group {0} has no supervisor."`, `"{0}: shares total {1}%. They must total 100%."`, `"{0}: {1} figure missing for {2}."`, `"Driver {0} has no employee."`, `"{0}: waiting for business input. {1}"`, `"Commission Settings: set the delivery charge account."`
  - `api.py` (all `@frappe.whitelist()`, check `frappe.has_permission` on Commission Plan): `get_commission_lines(plan, month) -> list[dict]`, `get_setup_status(plan, month) -> list[dict]` (one row per rule: name, category, summary, status, problems), `preview_tier(rule, amount, headcount=None) -> dict` (uses the same `calculate_tier`/`scale_tiers` path as the engine), `get_people(rule, month) -> list[dict]`, `save_people(rule, rows) -> None` (writes Commission Assignments), `get_missing_figure_grid(plan) -> dict`, `save_missing_figures(plan, rows) -> None`, `copy_plan(plan, new_name, valid_from, valid_to) -> str`.

- [ ] **Step 1: Failing tests** (build a small plan in the test with three rules):
  - Traditional salesperson, rolling, May 2026 with manual March 60,000 and April 90,000, May collected 120,000 → basis 90,000, tier "2 of 5", amount 367.
  - Same with April missing → status MISSING_DATA, amount 0, note names April 2026.
  - Salesman with no May activity but manual March/April → May counted as 0 (Review Focus 1).
  - Logistics waiting rule → WAITING lines with the note.
  - Sales Mgmt Company Sales = cash collected 900,000 + hypermarket invoiced 750,000 → 1,650,000 → 2,000 + 1,000 = 3,000; Manager 1,800, Assistant 1,200.
  - Smile24 driver with fees 1,500 and 130 free orders → 750 + 150 = 900.
  - Logistics with test tiers (800000, 5000) and 9 drivers + 2 workers, company sales 850,000 → below scaled 900,000 → 0; at 900,000 → drivers 3,000 total, workers 2,000 total.
  - `preview_tier(rule, 120000)` equals the engine's amount for basis 120,000.
  - `check_setup` lists "Sales Person Prabhu Test has no employee." with `fix == {"doctype": "Sales Person", "name": "Prabhu Test"}`.
- [ ] **Step 2–4:** FAIL → implement → PASS
- [ ] **Step 5: Commit** — `feat(commission): add calculation engine and setup check`
