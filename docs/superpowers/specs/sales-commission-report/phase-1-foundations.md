# Sales Commission Report – Phase 1: Foundations

> Read `plan-overview.md` first: it holds the global constraints, review focus and file map that apply to every task here.

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
