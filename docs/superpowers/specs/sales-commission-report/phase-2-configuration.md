# Sales Commission Report – Phase 2: Configuration DocTypes

> Read `plan-overview.md` first: it holds the global constraints, review focus and file map that apply to every task here.

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
