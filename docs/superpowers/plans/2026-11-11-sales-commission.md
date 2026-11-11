# Sales Commission & Incentive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One ERPNext report and setup tools that calculate every commission category from versioned, configurable rules, with a monthly approval run.

**Architecture:** Configuration DocTypes (Plan, Rule, Assignment, Manual Figure, Settings) feed a plain-Python engine in `sabaa/sabaa/commission/` built from small blocks (sources, periods, tiers, recipients, distribution). The script report, the Commission Run and the Desk setup page all call the engine through `commission/api.py`.

**Tech Stack:** Frappe 15 / ERPNext 15 / HRMS, Python 3.12, Desk JS (frappe.ui), `frappe.qb`.

**Spec:** `docs/superpowers/specs/2026-11-11-sales-commission-design.md` (read it with this plan).

## Global Constraints

- App `sabaa`, module `Sabaa`, branch `feat/sales-commission-v2`. Tabs for indentation (repo style).
- No fixtures. No `frappe.db.commit()` / `rollback()` in app code. Custom fields and roles come from patches in `sabaa/patches.txt`.
- `frappe.qb` / ORM, no raw SQL strings. Set-based reads: one query per source per date range, never per invoice.
- Status fields: one Select named `status`; transitions checked in the controller.
- Every amount that is not computable shows a status, never 0: `Ready`, `Needs setup`, `Waiting for business input`, `Missing data`, `Not assigned`.
- Collection accounts come from `Company.sales_collection_accounts` (Table MultiSelect of `Sales Collection Account`, field `sales_collection_account`).
- Company for tests and seed: `Saba Trading Group`. Currency QAR.
- Commits: Conventional Commits, no AI co-author line (user's CLAUDE.md overrides).
- Tests: `bench --site sabaa.local run-tests --app sabaa --module <dotted module>`. Integration tests use `FrappeTestCase` with a savepoint per test (pattern: `sabaa/sabaa/report/stock_ledger_quantity/test_stock_ledger_quantity.py`). Pure modules use `unittest.TestCase`.

**Decision taken while planning (from spec §8, builder's call):** "Fixed Step" and "Fixed + Excess %" are one formula, `fixed_amount + excess_percent/100 × (basis − threshold)` of the highest reached tier, with `excess_percent` 0 on rows that have none. `tier_method` therefore has three values: `Tiered`, `Flat Rate`, `Unit Rate`.

**Seeded tier rows** (threshold, fixed, excess %). "Up to X: A" in the map is read as "from the previous limit, pays A" (open question M1/SM1 stays flagged on the rule):

| Rule | Rows |
|---|---|
| Traditional – Salesperson | (70000,200,0) (84000,367,0) (105000,1050,0) (131250,2362.5,0) (157500,3937.5,3.5) |
| Traditional – Cashier Assistant | (70000,75,0) (84000,125,0) (105000,200,0) (131250,300,0) (157500,400,0.45) |
| Traditional – Supervisor | (672000,1344,0) (840000,2646,0) (1050000,4966.5,0) (1260000,7938,1) — base 8 |
| Modern – Salesperson Pool | (600000,1800,0) (700000,1800,1.25) (900000,2500,1.75) (1100000,3500,2) |
| Modern – Supervisor | (700000,1000,0) (900000,2000,0) (1100000,2000,1.5) |
| Sales Mgmt – Manager Pool | (1500000,2000,0) (1600000,2000,2) |
| Sales Mgmt – Coordinator | (1500000,350,0) |
| Smile24 – Online Salesperson | (20000,200,0) (30000,720,0) (50000,1700,0) (70000,2800,5) |
| Logistics – Team | none; `is_waiting_for_business` = 1, note "Logistics tiers not given (L1)"; base 8 |

## Review Focus

1. A salesman with no invoices or collections in one month of a 3-month average → that month is 0, not "Missing data". "Missing data" applies only to months before the first ERPNext invoice that also have no Manual Figure. Test in Task 8.
2. A customer return or credit note in a month bigger than that month's sales → net basis may be negative. The tier result is "below first tier" (0 QAR) and the negative value is shown, with no crash. Test in Task 3 and Task 6.
3. A sales person on an invoice with no Employee link, or a Driver with no employee → the line has status `Needs setup` with the name, and the amount stays visible as "Not assigned". Test in Task 8.
4. A plan edited after a run is approved → save is refused with a sentence naming the run. Test in Task 11.
5. Report run for a month that no Active plan covers → a message "No active commission plan covers <month>", not an empty table. Test in Task 10.

---

### Task 1: Clean start, package skeleton, settings, role and tender field

**Files:**
- Delete (ignored leftovers from the old branch, verify each holds only `__pycache__`): `sabaa/sabaa/commission/`, `sabaa/sabaa/doctype/commission_*/`
- Create: `sabaa/sabaa/commission/__init__.py`, `sabaa/sabaa/commission/tests/__init__.py`, `sabaa/sabaa/commission/constants.py`
- Create: DocType `Commission Settings` (Single) in `sabaa/sabaa/doctype/commission_settings/`
- Create: `sabaa/patches/create_commission_manager_role.py`, `sabaa/patches/add_is_tender_field_to_sales_invoice.py`
- Modify: `sabaa/patches.txt`
- Test: `sabaa/sabaa/doctype/commission_settings/test_commission_settings.py`

**Interfaces:**
- Produces: `constants.py` — `class Category(StrEnum)` with the six names; `class LineStatus(StrEnum)`: `READY="Ready"`, `NEEDS_SETUP="Needs setup"`, `WAITING="Waiting for business input"`, `MISSING_DATA="Missing data"`, `NOT_ASSIGNED="Not assigned"`; `COMMISSION_MANAGER = "Commission Manager"`.
- Produces: `Commission Settings` fields `company` (Link Company), `smile24_customer_group` (Link Customer Group, default `Online Sales`), `delivery_charge_account` (Link Account), `carton_uom` (Link UOM, default `Ctn`), `count_opening_balance_collections` (Check, default 1), `erpnext_start_date` (Date, reqd; first month with ERPNext data).

- [ ] **Step 1: Drop the old commission DocTypes from the dev site only**

Run a scratchpad script with `bench --site sabaa.local console` that calls `frappe.delete_doc("DocType", name, force=1, ignore_missing=True)` for: Commission Customer Group, Commission Item Rate, Commission Manual Sales, Commission Role Share, Commission Scheme, Commission Settings, Commission Team, Commission Team Member, Commission Tier, and `frappe.delete_doc("Report", "Sales Commission & Incentive", force=1, ignore_missing=True)`, then `frappe.db.commit()` (console only, not app code).
Expected: `frappe.db.exists("DocType", "Commission Scheme")` → `None`.

- [ ] **Step 2: Remove the leftover folders after `find <dir> -type f ! -path '*__pycache__*'` prints nothing**

- [ ] **Step 3: Write the failing test** — `test_settings_requires_erpnext_start_date`: saving settings without `erpnext_start_date` raises `frappe.MandatoryError`. `test_patches_created_role_and_field`: `frappe.db.exists("Role", "Commission Manager")` and `frappe.get_meta("Sales Invoice").has_field("is_tender")`.

- [ ] **Step 4: Create the DocType, the two patches (pattern: `sabaa/patches/add_sales_collection_accounts_field_to_company.py`, but no `try/except` swallow) and register them under `[post_model_sync]`.** `is_tender`: Check, label "Tender Sale", insert after `customer`, `allow_on_submit` 0, `module` "Sabaa". Settings permissions: System Manager and Commission Manager write.

- [ ] **Step 5: `bench --site sabaa.local migrate`, run the test, expect PASS**

- [ ] **Step 6: Commit** — `feat(commission): add settings, role and tender field`

---

### Task 2: Tier calculation (pure)

**Files:**
- Create: `sabaa/sabaa/commission/tiers.py`, `sabaa/sabaa/commission/tests/test_tiers.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Tier: threshold: float; fixed_amount: float; excess_percent: float = 0`
  - `@dataclass(frozen=True) class TierResult: tier_number: int | None; tier_count: int; threshold: float | None; next_threshold: float | None; fixed_part: float; excess_part: float` with `@property amount` and `@property gap_to_next` (`None` at the last tier).
  - `calculate_tier(basis: float, tiers: list[Tier]) -> TierResult` — highest tier with `threshold <= basis` (inclusive); below the first → `tier_number=None`, amounts 0.
  - `scale_tiers(tiers, actual_headcount: int, base_headcount: int, scale_amounts: bool = False) -> list[Tier]` — threshold × actual/base; amounts too only when `scale_amounts`. `base_headcount == 0` returns the tiers unchanged.
  - `flat_rate(basis: float, percent: float) -> float`
  - `validate_tiers(tiers) -> list[str]` — plain-language problems: thresholds not strictly increasing, negative values, percent > 100.

- [ ] **Step 1: Write failing tests** (values from the seeded table):

```python
SALESPERSON = [Tier(70000,200),Tier(84000,367),Tier(105000,1050),Tier(131250,2362.5),Tier(157500,3937.5,3.5)]
def test_below_first_tier(): r = calculate_tier(69999.99, SALESPERSON); assert r.tier_number is None and r.amount == 0 and r.next_threshold == 70000
def test_threshold_is_inclusive(): assert calculate_tier(84000, SALESPERSON).amount == 367
def test_fixed_step_keeps_previous_tier(): assert calculate_tier(104999, SALESPERSON).amount == 367
def test_excess_on_last_tier(): assert calculate_tier(167500, SALESPERSON).amount == 3937.5 + 350
def test_tier_number_and_gap(): r = calculate_tier(120000, SALESPERSON); assert (r.tier_number, r.tier_count, r.gap_to_next) == (3, 5, 11250)
def test_negative_basis(): assert calculate_tier(-500, SALESPERSON).amount == 0
def test_scale_targets_only(): t = scale_tiers([Tier(800000, 5000)], 9, 8); assert t[0].threshold == 900000 and t[0].fixed_amount == 5000
def test_scale_amounts_when_asked(): assert scale_tiers([Tier(800000, 5000)], 9, 8, True)[0].fixed_amount == 5625
def test_modern_pool_excess(): pool = [Tier(600000,1800),Tier(700000,1800,1.25),Tier(900000,2500,1.75),Tier(1100000,3500,2)]; assert calculate_tier(800000, pool).amount == 3050
def test_flat_rate_tender(): assert flat_rate(50000, 1.5) == 750
def test_validate_tiers_order(): assert validate_tiers([Tier(2,1),Tier(1,1)]) == ["Tier 2 must start above tier 1 (1 is not above 2)."]
```

- [ ] **Step 2: Run** `bench --site sabaa.local run-tests --app sabaa --module sabaa.sabaa.commission.tests.test_tiers` — expect FAIL (import error)
- [ ] **Step 3: Implement `tiers.py`** (round money with `frappe.utils.flt(x, 2)`)
- [ ] **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** — `feat(commission): add tier calculation`

---

### Task 3: Periods and averages (pure)

**Files:** Create `sabaa/sabaa/commission/periods.py`, `sabaa/sabaa/commission/tests/test_periods.py`

**Interfaces:**
- Produces:
  - `class PeriodMode(StrEnum)`: `MONTHLY="Monthly"`, `QUARTERLY="Quarterly Average"`, `ROLLING="Rolling 3-Month Average"`
  - `get_basis_months(mode: PeriodMode, payout_month: date) -> list[date] | None` — first-of-month dates; `None` = the rule does not pay in this month (Quarterly when the month is not Mar/Jun/Sep/Dec).
  - `average_of_months(values: dict[date, float | None], months: list[date]) -> float | None` — `None` if any month is `None`; months with no rows must be passed as `0.0` by the caller, not `None`.
  - `month_start(d) -> date`, `month_end(d) -> date`.

- [ ] **Step 1: Failing tests:** `get_basis_months(MONTHLY, 2026-05-01) == [2026-05-01]`; `ROLLING, 2026-05-01 → [03-01, 04-01, 05-01]`; `QUARTERLY, 2026-05-01 → None`; `QUARTERLY, 2026-06-15 → [04-01, 05-01, 06-01]`; `ROLLING, 2026-01-01 → [2025-11-01, 2025-12-01, 2026-01-01]`; `average_of_months({…60000, 90000, 120000}) == 90000`; with one `None` → `None`; with a negative month `(-3000, 0, 3000)` → `0`.
- [ ] **Step 2: Run, expect FAIL** · **Step 3: Implement** · **Step 4: Run, expect PASS**
- [ ] **Step 5: Commit** — `feat(commission): add period and average rules`

---

### Task 4: Plan and Rule DocTypes

**Files:**
- Create DocTypes in `sabaa/sabaa/doctype/`: `commission_plan`, `commission_rule`, child tables `commission_tier`, `commission_basis_source`, `commission_unit_rate`, `commission_share`, and Table MultiSelect children `commission_excluded_group` (Link Customer Group), `commission_designation` (Link Designation)
- Test: `sabaa/sabaa/doctype/commission_plan/test_commission_plan.py`, `sabaa/sabaa/doctype/commission_rule/test_commission_rule.py`

**Interfaces:**
- Consumes: `tiers.validate_tiers`, `tiers.Tier`, `periods.PeriodMode`, `constants.Category`.
- Produces fields exactly as spec §6.1 with these names and values:
  - Commission Plan: `plan_name` (Data, unique, autoname `field:plan_name`), `company`, `valid_from`, `valid_to`, `status` Select `Draft\nActive\nClosed`, `excluded_customer_groups` (Table MultiSelect → Commission Excluded Group).
  - Commission Rule: autoname `format:{plan}-{rule_name}`; `plan`, `rule_name`, `category` (Select of the six), `role_label`, `template` (Data, read-only, set by the template dialog), `basis` Select `Collected Sales\nNet Invoiced Sales\nCompany Sales\nDelivery Fees\nUnit Count\nTender Collections\nPaired Basis`, `basis_sources` (Table → Commission Basis Source: `customer_group`, `measure` Select `Collected\nInvoiced`), `attribute_by` Select `Invoice Sales Person\nInvoice Driver\nNone`, `period_mode` (PeriodMode values), `payout_multiplier` Int default 1, `tier_method` Select `Tiered\nFlat Rate\nUnit Rate`, `tiers` (Table → Commission Tier: `threshold`, `fixed_amount`, `excess_percent`), `flat_rate_percent`, `unit_rates` (Table → Commission Unit Rate: `item`, `uom`, `amount_per_unit`), `bonus_after_count` Int, `bonus_per_unit` Currency, `headcount_base` Int, `headcount_share` Data (name of the share whose member count scales the tiers; empty = team members), `scale_amounts` Check, `recipient_source` Select `Each Attributed Person\nSupervisor of Sales Person Group\nPool`, `team_group` (Link Sales Person, filter `is_group=1`), `member_designations` (Table MultiSelect → Commission Designation), `paired_rule` (Link Commission Rule), `shares` (Table → Commission Share: `share_name`, `percent`, `designation`, `department`, `split` Select `Equal\nBy Assignment %`), `is_waiting_for_business` Check, `status_note` Small Text, `summary` (Small Text, read-only, filled in `validate`).
  - `CommissionRule.get_tiers(self) -> list[Tier]` and `CommissionRule.get_summary(self) -> str` (e.g. "5 tiers · Rolling 3-Month Average · Collected Sales").
  - `CommissionPlan.get_active_plan(company: str, month: date) -> str | None` (staticmethod).
- Form layout (spec §6.5.2): tabs/sections in order Summary · Tiers · People & Split · Period · Advanced (collapsible, collapsed) holding basis, basis_sources, attribute_by, recipient_source, headcount fields, payout_multiplier, paired_rule. `depends_on` hides `tiers` unless Tiered, `flat_rate_percent` unless Flat Rate, `unit_rates` unless Unit Rate, `shares` unless Pool, `team_group` unless recipient source uses it.
- Permissions: Commission Manager full; Sales Manager and Accounts Manager read.

- [ ] **Step 1: Failing tests:**
  - `test_active_plans_cannot_overlap` — second Active plan for the same company with overlapping dates raises `frappe.ValidationError` whose message names the first plan.
  - `test_get_active_plan` returns the plan for 2026-05-15 and `None` for 2027-01-01 when the plan ends 2026-12-31.
  - `test_rule_rejects_unordered_tiers` — message equals the `validate_tiers` sentence.
  - `test_pool_shares_must_total_100` — shares 60 + 35 raise "Shares total 95%. They must total 100%."
  - `test_summary_is_filled` — `rule.summary == "5 tiers · Rolling 3-Month Average · Collected Sales"`.
  - `test_waiting_rule_may_have_no_tiers` — Tiered rule with no tiers saves only when `is_waiting_for_business` is set; else "Add at least one tier, or tick Waiting for business input."
- [ ] **Step 2: Run, expect FAIL** · **Step 3: Create DocTypes and controllers** · **Step 4: migrate, run, expect PASS**
- [ ] **Step 5: Commit** — `feat(commission): add commission plan and rule`

---

### Task 5: Assignment and Manual Figure DocTypes

**Files:** Create `sabaa/sabaa/doctype/commission_assignment/`, `sabaa/sabaa/doctype/commission_manual_figure/` with tests.

**Interfaces:**
- Produces:
  - Commission Assignment: `rule` (Link Commission Rule, reqd), `employee` (reqd), `assignment_type` Select `Assistant Of\nPool Share %\nShare Member\nExclude\nInclude`, `target_sales_person` (Link Sales Person; reqd for Assistant Of), `share_name` (Data; reqd for Share Member, must exist in the rule's shares), `percent` (reqd for Pool Share %), `from_date` (reqd), `to_date`.
  - `get_assignments(rule: str, start: date, end: date, assignment_type: str | None = None) -> list[frappe._dict]` in `commission_assignment.py` — rows whose dates overlap the range.
  - Commission Manual Figure: `plan` (reqd), `month` (Date, normalized to first of month in `validate`), `rule` (Link Commission Rule, reqd), `sales_person` (Link Sales Person, empty = rule-level total), `amount` (Currency), `source_note`. Unique on (rule, month, sales_person). `validate` refuses months on or after `Commission Settings.erpnext_start_date`.
  - `get_manual_figures(rule: str, months: list[date]) -> dict[tuple[date, str | None], float]`.

- [ ] **Step 1: Failing tests:** overlapping-date lookup returns the row for May when `from_date` 2026-04-15 and `to_date` empty; Assistant Of without `target_sales_person` fails with "Choose the salesman this assistant works with."; Manual Figure for 2026-05 fails with "May 2026 is in ERPNext. Manual figures are only for months before 2026-05-01."; duplicate figure fails.
- [ ] **Step 2–4:** FAIL → implement → PASS
- [ ] **Step 5: Commit** — `feat(commission): add assignments and manual figures`

---

### Task 6: Sales sources — collected and invoiced

**Files:** Create `sabaa/sabaa/commission/sources.py`, `sabaa/sabaa/commission/tests/test_sources.py`, `sabaa/sabaa/commission/tests/factories.py` (shared builders: customer in group, sales person with employee, invoice with sales team, payment entry, journal entry).

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class BasisRow: month: date; key: str | None; amount: float; flag: str | None = None` — `key` is the sales person (or driver employee) the amount belongs to; `None` = unattributed.
  - `expand_customer_groups(groups: list[str], excluded: list[str]) -> list[str]` (descendants via lft/rgt, minus excluded and their descendants).
  - `get_invoiced(company, customer_groups, from_date, to_date, exclude_items: list[str] = ()) -> list[BasisRow]` — `base_net_total` of submitted invoices incl. returns (negative), per posting month and invoice sales person; `exclude_items` subtracts those items' `base_net_amount`.
  - `get_collected(company, customer_groups, from_date, to_date, exclude_items: list[str] = ()) -> list[BasisRow]` — per payment month:
    - Payment Ledger Entry rows, `party_type` Customer, `delinked` 0, `amount < 0`, `voucher_type` in (Payment Entry, Journal Entry), whose voucher has a GL row on an account in `Company.sales_collection_accounts`; exclude `is_opening` vouchers.
    - POS `paid_amount − change_amount` of `is_pos` invoices, by posting month.
    - Attribution: `against_voucher` is a Sales Invoice → its sales person; against the opening entry → if `count_opening_balance_collections`, the customer's latest invoice sales person with flag `"opening balance"`, else skipped; unallocated → the customer's latest invoice before the payment date with flag `"attributed by customer"`; no invoice at all → `key=None`, flag `"no sales person"`.
    - `exclude_items` subtracts those items' invoiced net amount for invoices posted in the same month by the same sales person.
- Excluded groups always include the plan's `excluded_customer_groups` (callers pass them).

- [ ] **Step 1: Failing integration tests** (FrappeTestCase, savepoint per test, factories):
  - `test_invoiced_nets_returns` — 10,000 invoice + 2,500 return in May → one row 7,500.
  - `test_direct_sales_excluded` — invoice in `Direct Sales` group absent.
  - `test_collected_allocated_payment` — invoice 4/2026-05-03 by "SP A", payment entry 2026-06-02 to a collection account → row (June, "SP A", amount).
  - `test_credit_note_journal_not_collected` — JE crediting the customer against a non-collection account → no row.
  - `test_unallocated_journal_attributed_by_customer` — flag `"attributed by customer"`.
  - `test_pos_paid_amount_counted`.
  - `test_unit_items_removed_from_collected_basis` — 1,000 sale with 200 of Tea Milk, collected 1,000 → 800.
  - `test_negative_month_allowed` — return larger than sales → negative row, no error (Review Focus 2).
- [ ] **Step 2–4:** FAIL → implement → PASS
- [ ] **Step 5: Commit** — `feat(commission): read collected and invoiced sales`

---

### Task 7: Other sources — delivery fees, units, tender collections

**Files:** Modify `sabaa/sabaa/commission/sources.py`; test `sabaa/sabaa/commission/tests/test_sources_other.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class DeliveryRow: month: date; driver: str | None; employee: str | None; fee_amount: float; free_order_count: int`
  - `get_delivery_fees(company, customer_groups, from_date, to_date, account: str) -> list[DeliveryRow]` — fee = invoice item rows (and tax rows) booked to `account`; free order = invoice with no such row; grouped by month and `Sales Invoice.driver` → `Driver.employee`.
  - `get_units(company, customer_groups, from_date, to_date, unit_rates: list[frappe._dict], carton_uom: str) -> list[BasisRow]` — `amount` = cartons × `amount_per_unit`, cartons = `stock_qty / conversion_factor(item, carton_uom)`, returns negative (U1 default), attributed to the invoice sales person.
  - `get_tender_collections(company, from_date, to_date) -> list[BasisRow]` — `get_collected` limited to allocations against invoices with `is_tender = 1`; `key=None` (pool).

- [ ] **Step 1: Failing tests:** two Smile24 invoices with 15 QAR delivery and one without, same driver → `fee_amount == 30`, `free_order_count == 1`; Driver without employee → `employee is None`; 96 Pcs of Tea Milk at 48/Ctn with rate 1 → amount 2; tender invoice 100,000 with 50,000 collected in June → June row 50,000, nothing in May.
- [ ] **Step 2–4:** FAIL → implement → PASS
- [ ] **Step 5: Commit** — `feat(commission): read delivery fees, units and tender collections`

---

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

---

### Task 10: Default plan, templates and the report

**Files:**
- Create: `sabaa/sabaa/commission/templates.py`, `sabaa/sabaa/commission/default_plan.py`
- Create: report `sabaa/sabaa/report/sales_commission_and_incentive/` (report name "Sales Commission & Incentive", Script Report, ref DocType Commission Plan, roles Commission Manager, Sales Manager, Accounts Manager)
- Tests: `test_default_plan.py`, `sabaa/sabaa/report/sales_commission_and_incentive/test_sales_commission_and_incentive.py`

**Interfaces:**
- Produces:
  - `templates.py`: `RULE_TEMPLATES: dict[str, dict]` — one entry per row of spec §6.3 (key = template name such as `"Traditional Trade – Salesperson"`), each holding the field values and tier rows from this plan's Seeded tier rows table. `get_templates() -> list[dict]` (whitelisted through api) and `apply_template(rule_doc, template_name) -> None`.
  - `create_default_plan(company: str, valid_from="2026-01-01", valid_to="2026-06-30") -> str` — plan "Commission Map Jan–Jun 2026", status Draft, excluded `Direct Sales`, one rule per template; idempotent (returns the existing plan). Rules waiting by default: Logistics (L1), Tenders (T1/T2), Modern pool (M2), Cashier Assistant (S2); their notes cite the open question code.
  - Report `execute(filters)`: filters `company`, `plan` (optional; default `get_active_plan`), `period_type` Select `Month\nQuarter`, `month` (Date, any day in the month) or `quarter` Select `2026-Q1…`, `category`, `employee`, `view` Select `Summary by Employee\nDetail` (default Summary). Quarter view = sum of the three monthly engine runs. Summary: one row per employee, one Currency column per category, `total`; a final "Not assigned" row. Detail: columns from `CommissionLine` in spec §6.4 order, `tier_label` like "2 of 5". `message` (report message) holds setup problems as HTML links and the run banner. No plan → return no rows and the message `_("No active commission plan covers {0}.")` with the month as "May 2026". Do not throw (Review Focus 5).
  - JS: month picker as a Date field whose `on_change` normalizes to the first of the month; status column formatter with Frappe indicator colors (green Ready, orange Needs setup/Missing data, grey Waiting, red Not assigned).

- [ ] **Step 1: Failing tests:** default plan creates 12 rules and is idempotent; tier rows of "Traditional Trade – Supervisor" equal the seeded table; report Summary has one row per employee plus "Not assigned"; Detail row has `tier_label == "2 of 5"`; no plan for 2030-01 → empty data and the message text; Quarter Q2 equals sum of Apr/May/Jun runs.
- [ ] **Step 2–4:** FAIL → implement → PASS
- [ ] **Step 5: Commit** — `feat(commission): add default plan and commission report`

---

### Task 11: Commission Run and locking

**Files:** Create DocTypes `commission_run` (submittable) and `commission_run_line` (child); modify `commission_rule.py`, `commission_assignment.py`, `commission_manual_figure.py` controllers; tests `test_commission_run.py`.

**Interfaces:**
- Consumes: `CommissionEngine`, `CommissionLine.as_dict()`.
- Produces:
  - Commission Run: `plan`, `company`, `month` (first of month), `status` Select `Draft\nCalculated\nApproved\nPaid\nCancelled`, `total_amount`, `not_assigned_amount`, `employee_count`, `journal_entry` (Link, optional), `lines` (Table → Commission Run Line, fields = CommissionLine minus `month_values`, plus `month_values_text`).
  - Methods: `calculate(self)` (whitelisted; Draft/Calculated only), `on_submit` → Approved (refuses while any line is NEEDS_SETUP or MISSING_DATA: "Fix the setup problems before approval."), `mark_paid(self, journal_entry=None)` (Approved only), `on_cancel` → Cancelled. `validate` refuses a second non-cancelled run for the same plan + month, naming it. `get_live_difference(self) -> float`.
  - `is_month_locked(plan: str, month: date) -> str | None` in `commission_run.py` — returns the run name if Approved or Paid.
  - Locks: Commission Rule `validate` refuses changes to tiers, shares, basis fields, period, multiplier when its plan has any Approved/Paid run: "Run {0} is approved. Copy the plan to change the rules." Assignments and Manual Figures dated in a locked month refuse save and delete with "{0} is approved for {1}."
  - Form JS: one primary button per status (Calculate / Approve / Mark Paid); Approve confirm dialog showing total, employee count, not-assigned amount; dashboard headline "Changes since approval: {difference} QAR" when non-zero.

- [ ] **Step 1: Failing tests:** status transitions Draft→Calculated→Approved→Paid; Paid→Calculated refused; duplicate run refused; approve with a NEEDS_SETUP line refused; editing a tier after approval refused (Review Focus 4); manual figure in a locked month refused; cancel unlocks.
- [ ] **Step 2–4:** FAIL → implement → PASS
- [ ] **Step 5: Commit** — `feat(commission): add commission run with approval and locking`

---

### Task 12: Commission Setup page and guided forms

**Files:**
- Create: Desk Page `sabaa/sabaa/page/commission_setup/` (`commission_setup.json`, `.js`, `.css` small), roles Commission Manager
- Create: `sabaa/sabaa/doctype/commission_rule/commission_rule.js`, `sabaa/sabaa/doctype/commission_plan/commission_plan.js`, `sabaa/public/js/commission/people_dialog.js`, `sabaa/public/js/commission/missing_figures_dialog.js` (bundled via `app_include_js` only if Page/form need them, else `frappe.require`)
- Modify: `sabaa/sabaa/workspace/` — add a shortcut "Commission Setup" and the report to the existing Sabaa workspace
- Test: `sabaa/sabaa/commission/tests/test_api_ui.py` (server side of each dialog)

**Interfaces:**
- Consumes: `api.get_setup_status`, `api.preview_tier`, `api.get_people`, `api.save_people`, `api.get_missing_figure_grid`, `api.save_missing_figures`, `api.copy_plan`, `default_plan.create_default_plan`, `templates.get_templates`.
- Behaviour (spec §6.5, copy exact):
  - Page header: Plan and Month fields; primary button "Check setup"; it runs on load. Empty state when no plan: "No commission plan yet." + primary "Create default plan".
  - Body: groups by category; each rule row = name, status indicator, summary line, then problems as "<message> → Fix". Fix opens the doc (`frappe.set_route`) or the People / Missing figures dialog.
  - Secondary actions: "Copy plan to new period" (dialog: new name, from, to), "Open report" (route to the report with plan and month).
  - Rule form: "New rule" from a plan opens a template picker dialog (grouped by category). Tier grid row label formatter: "From 70,000 QAR → 200 QAR (+3.5% above)". "Try an amount" Currency field in the Tiers section showing `preview_tier` result text: "120,000 → Tier 3 of 5 → 1,050 QAR" and, with scaling, "Target for 9 drivers: 900,000".
  - People dialog: table of members with a source badge, Exclude toggle, Share % for pools, "Add assistant" (employee + salesman); live footer "100% ✓" or "95%, 5% missing"; Save disabled while shares are not 100%.
  - Missing figures dialog: grid rows = sales persons/Company, columns = missing months; a "Paste from Excel" textarea that parses tab-separated rows.

- [ ] **Step 1: Failing tests (server):** `get_setup_status` returns 12 rows for the default plan with statuses; `save_people` with Exclude row creates an Exclude assignment from the month start; `save_people` with shares 95% raises "Shares total 95%. They must total 100%."; `save_missing_figures` round-trips through `get_missing_figure_grid`.
- [ ] **Step 2–4:** FAIL → implement page, dialogs and form scripts → PASS; `bench build --app sabaa` succeeds.
- [ ] **Step 5: Browser check with agent-browser** (spec §6.5 UX acceptance): on a fresh test plan, create default plan → fix Smile24 problems via Fix links → Smile24 rule shows Ready, without opening a list view or Advanced. Every problem has a working Fix link. "Try an amount" value equals the report Detail amount for the same basis. Take screenshots into the scratchpad. Run the `ui-design` review checklist and fix findings.
- [ ] **Step 6: Commit** — `feat(commission): add commission setup page and guided forms`

---

### Task 13: Validation on real data and handover docs

**Files:** Create `docs/commission-configuration-guide.md` (for the client admin, technical-writing style), `docs/superpowers/progress/sales-commission-v2.md` (validation results).

- [ ] **Step 1:** Run full suite: `bench --site sabaa.local run-tests --app sabaa --module sabaa.sabaa.commission.tests` plus each DocType and report test. Expect all PASS. Record counts.
- [ ] **Step 2:** On `sabaa.local`: create the default plan, set Commission Settings (`erpnext_start_date` 2026-05-01, delivery charge account `4203 - Delivery Charges`), run the report for May and June 2026 (Month and Q2 Quarter, both views), export to Excel, and time each run (must finish under the report timeout).
- [ ] **Step 3:** Compare May/June totals per category with the commission expense account balances; write each difference and its cause (open question, missing setup, or bug) in the progress file. Fix any bug found with a regression test first.
- [ ] **Step 4:** Write the admin guide: first setup, monthly routine (Check setup → report → run → approve → mark paid), new period, answering an open question (which field to change for each code G1–U1).
- [ ] **Step 5:** Run `frappe-code-review` skill on the branch diff; fix findings.
- [ ] **Step 6: Commit** — `docs(commission): add admin guide and validation results`
