# Sales Commission & Incentive Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One ERPNext report and setup tools that calculate every commission category from versioned, configurable rules, with a monthly approval run.

**Architecture:** Configuration DocTypes (Plan, Rule, Assignment, Manual Figure, Settings) feed a plain-Python engine in `sabaa/sabaa/commission/` built from small blocks (sources, periods, tiers, recipients, distribution). The script report, the Commission Run and the Desk setup page all call the engine through `commission/api.py`.

**Tech Stack:** Frappe 15 / ERPNext 15 / HRMS, Python 3.12, Desk JS (frappe.ui), `frappe.qb`.

**Spec:** `docs/superpowers/specs/sales-commission-report/design.md` (read it with this plan).

**Phase files:** `phase-1-foundations.md` to `phase-7-validation-and-handover.md` in this folder. Progress: `docs/superpowers/progress/sales-commission-report.md`.

## Global Constraints

- App `sabaa`, module `Sabaa`, branch `feat/sales-commission-v2`. Tabs for indentation (repo style).
- No fixtures. No `frappe.db.commit()` / `rollback()` in app code. Custom fields and roles come from patches in `sabaa/patches.txt`.
- `frappe.qb` / ORM, no raw SQL strings. Set-based reads: one query per source per date range, never per invoice.
- Status fields: one Select named `status`; transitions checked in the controller.
- Every amount that is not computable shows a status, never 0: `Ready`, `Needs setup`, `Waiting for business input`, `Missing data`, `Not assigned`.
- Collection accounts come from `Company.sales_collection_accounts` (Table MultiSelect of `Sales Collection Account`, field `sales_collection_account`).
- Company for tests and seed: `Saba Trading Group`. Currency QAR.
- Commits: Conventional Commits, no AI co-author line (user's CLAUDE.md overrides).
- Tests run from `/home/work/saba-bench`. If the site refuses with "Testing is disabled", stop and ask the user before running `bench --site sabaa.local set-config allow_tests true`.
- After any DocType JSON change run `bench --site sabaa.local migrate`.
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

## Phases

| Phase | File | Tasks |
|---|---|---|
| 1 | `phase-1-foundations.md` | 1, 2, 3 |
| 2 | `phase-2-configuration.md` | 4, 5 |
| 3 | `phase-3-sources.md` | 6, 7 |
| 4 | `phase-4-engine.md` | 8, 9 |
| 5 | `phase-5-report-and-run.md` | 10, 11 |
| 6 | `phase-6-setup-ux.md` | 12 |
| 7 | `phase-7-validation-and-handover.md` | 13 |

## File Map

| Path | Responsibility |
|---|---|
| `sabaa/sabaa/commission/constants.py` | `Category`, `LineStatus`, role name |
| `sabaa/sabaa/commission/tiers.py` | `Tier`, `TierResult`, `calculate_tier`, `scale_tiers`, `flat_rate`, `validate_tiers` |
| `sabaa/sabaa/commission/periods.py` | `PeriodMode`, basis months, averages |
| `sabaa/sabaa/commission/sources.py` | Collected, invoiced, delivery fees, units, tender collections |
| `sabaa/sabaa/commission/recipients.py` | Tree members, supervisors, designation members, overrides |
| `sabaa/sabaa/commission/distribution.py` | `Allocation`, `split_pool` |
| `sabaa/sabaa/commission/engine.py` | `CommissionLine`, `CommissionEngine` |
| `sabaa/sabaa/commission/setup_check.py` | `SetupProblem`, `check_setup` |
| `sabaa/sabaa/commission/api.py` | Whitelisted endpoints for report, run, page and dialogs |
| `sabaa/sabaa/commission/templates.py` | Rule templates per category |
| `sabaa/sabaa/commission/default_plan.py` | Idempotent default plan |
| `sabaa/sabaa/commission/tests/` | Unit and integration tests, `factories.py` |
| `sabaa/sabaa/doctype/commission_*/` | Settings, Plan, Rule and children, Assignment, Manual Figure, Run and Run Line |
| `sabaa/sabaa/report/sales_commission_and_incentive/` | The Script Report |
| `sabaa/sabaa/page/commission_setup/` | The Desk setup page |
| `sabaa/public/js/commission/` | People and missing-figures dialogs |
| `sabaa/patches/` | Commission Manager role, `is_tender` field |
| `docs/commission-configuration-guide.md` | Admin guide |

Every new package folder gets an empty `__init__.py`.
