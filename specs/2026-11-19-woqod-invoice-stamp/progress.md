# Woqod Invoice Stamp: Progress

**Design:** [design.md](design.md) · **Plan:** [plan.md](plan.md) · **Tests:** [test-plan.md](test-plan.md)
Branch: `feat/woqod-invoice-stamp`. Worktree: `/home/work/saba-bench/sabaa-invoice-stamp`.
Analysis page with the saved answers: https://claude.ai/artifact/THp6Va2zxb5UPQDUxuLkQ3

## Status

| Phase | Tasks | Status | Tests | Review |
|---|---|---|---|---|
| 1 Fields and stamp rule | 1, 2 | Not started | - | - |
| 2 Print format | 3 | Not started | - | - |
| 3 Validation and handover | 4 | Not started | - | - |

## Decisions

- 19 Nov 2026: The user answered Q1 to Q4 and Q6 to Q11 on the analysis page. All answers are A.
- 19 Nov 2026: The user answered Q5 in chat: A (the stamp follows the invoice brand).
- 19 Nov 2026: Follow-up on Q10 in chat: App Settings is in van_sales, so a sabaa patch adds the stamp fields as custom fields. van_sales does not change.

## Open items

- The client sends the Saba and Green World stamps as transparent PNG files.
- Confirm the Woqod group names on staging and production.
- Before the first test, agree with the user how the bench loads this worktree (`apps/sabaa` has uncommitted work on `feat/customer-group-ledger-summary`).

## Log

- 19 Nov 2026: Branch, spec, plan and test plan made (95e6eeb). Draft PR: https://github.com/akwadqa/sabaa/pull/8
- 19 Nov 2026: Moved the files to `specs/2026-11-19-woqod-invoice-stamp/`, as the user asked. The phases are now in `plan.md`.
