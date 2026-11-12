# Progress: Sales Commission & Incentive Report

Branch: `feat/sales-commission-v2`
Spec folder: `docs/superpowers/specs/sales-commission-report/`

Update this file when a task starts, finishes or is blocked. Record the commit hash and test result.

## Phase 1: Foundations (`phase-1-foundations.md`) — complete at a15de5e

- [x] Task 1: Clean start, package skeleton, settings, role and tender field — done (c8980a3), 2 tests passing
- [x] Task 2: Tier calculation (pure) — done (b839028, fix cd20e48), 18 tests passing
- [x] Task 3: Periods and averages (pure) — done (a15de5e), 12 tests passing

## Phase 2: Configuration DocTypes (`phase-2-configuration.md`) — complete at d375e30

- [x] Task 4: Plan and Rule DocTypes — done (bbd88ca, fix d742e12), 13 tests passing
- [x] Task 5: Assignment and Manual Figure DocTypes — done (ab383fe, fix d375e30), 18 tests passing

## Phase 3: Sources (`phase-3-sources.md`) — complete at ce6f851

- [x] Task 6: Sales sources — collected and invoiced — done (40414a2, fix 97fac5a), 18 tests passing
- [x] Task 7: Other sources — delivery fees, units, tender collections — done (ce6f851), 5 tests passing

## Phase 4: Recipients and engine (`phase-4-engine.md`) — complete at a4bafd4

- [x] Task 8: Recipients and distribution — done (90db238), 11 tests passing
- [x] Task 9: Engine, setup check and API — done (a4bafd4), 10 tests passing

## Phase 5: Report and Commission Run (`phase-5-report-and-run.md`) — complete at 2ed98bc

- [x] Task 10: Default plan, templates and the report — done (cf35d36), 7 tests passing
- [x] Task 11: Commission Run and locking — done (2ed98bc), 5 tests passing

## Phase 6: Client setup UX (`phase-6-setup-ux.md`)

- [x] Task 12: Commission Setup page and guided forms — done (028a403), 4 tests passing; browser check pending

## Phase 7: Validation and handover (`phase-7-validation-and-handover.md`)

- [x] Task 13: Validation on real data and handover docs — done; suite 125 tests passing (1 skipped)

## Final review

Whole-branch review found 2 Critical and 8 Important issues; all fixed in c329c11 with regression tests. 16 Minor items are deferred (see final message). Suite: 16 modules, 132 tests OK, 1 skipped.

## Validation on real data (sabaa.local, 2026-11-12)

Default plan created; Commission Settings: start 2026-05-01, delivery account `4203 - Delivery Charges - STG`.

| Month | Run time | Lines | Result |
|---|---|---|---|
| May 2026 | 0.67 s | 16 | Smile24 1,794.75 QAR, Tea Milk 27.54 QAR. Quarterly rules do not pay in May. |
| June 2026 | 1.08 s | 25 | Quarterly rules show "Missing data": April figures are not entered yet. |

Setup problems found on the site (shown with Fix links): 5 Smile24 drivers without an employee, 4 cash sales persons without an employee (Prabhu, Mehtab, Morgon, Shohail), no supervisor set on the two Sales Person groups, missing April figures.

Comparison with booked commission: May 2026 bookings (51302 Cash 27,673; 51306 Drivers and Labor 10,756; 51308 H.M 14,063; 51310 Management 17,662; 51320 Sales Head 26,601; 51322 Smile 24 5,262) are the January–April catch-up. A like-for-like comparison needs the March and April figures and the open answers (G4, S1, M2, L1). Bugs found in this run and fixed with regression tests: invoices without a driver, and figure requests for sales people outside the team.

Not done yet: browser check of the setup screens (needs the web server and a browser; held back to save laptop memory).
