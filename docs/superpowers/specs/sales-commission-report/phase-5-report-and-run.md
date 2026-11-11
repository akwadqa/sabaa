# Sales Commission Report – Phase 5: Report and Commission Run

> Read `plan-overview.md` first: it holds the global constraints, review focus and file map that apply to every task here.

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
