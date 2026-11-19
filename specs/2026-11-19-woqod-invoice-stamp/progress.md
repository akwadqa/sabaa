# Woqod Invoice Stamp: Progress

**Design:** [design.md](design.md) · **Plan:** [plan.md](plan.md) · **Tests:** [test-plan.md](test-plan.md)
Branch: `feat/woqod-invoice-stamp`, checked out in `apps/sabaa`.
Analysis page with the saved answers: https://claude.ai/artifact/THp6Va2zxb5UPQDUxuLkQ3

## Status

| Phase | Tasks | Status | Tests | Review |
|---|---|---|---|---|
| 1 Fields and stamp rule | 1, 2 | Done (46b0295, fb9f080) | 17 pass | Done, no fixes |
| 2 Print format | 3 | Done (e7b7960, 0874c7b) | 3 pass (20 in all) | Done, 1 fix |
| 3 Validation and handover | 4 | In progress: tests, lint and guide done. Staging steps wait for the user | 20 pass | Per phase done |

## Decisions

- 19 Nov 2026: The user answered Q1 to Q4 and Q6 to Q11 on the analysis page. All answers are A.
- 19 Nov 2026: The user answered Q5 in chat: A (the stamp follows the invoice brand).
- 19 Nov 2026: Follow-up on Q10 in chat: App Settings is in van_sales, so a sabaa patch adds the stamp fields as custom fields. van_sales does not change.

- 19 Nov 2026: The user asked to work on the branch in `apps/sabaa`, not in a worktree. The Customer Group Ledger Summary work was committed on its own branch (7cb022d), the worktree was removed, and `apps/sabaa` now has `feat/woqod-invoice-stamp`.

## Open items

- The client sends the Saba and Green World stamps as transparent PNG files.
- Confirm the Woqod group names on staging and production.
- Stamp size and position: 70 px on the Authorized Signature line. Confirm with the client when the real stamps arrive.

## Log

- 19 Nov 2026: Branch, spec, plan and test plan made (95e6eeb). Draft PR: https://github.com/akwadqa/sabaa/pull/8
- 19 Nov 2026: Moved the files to `specs/2026-11-19-woqod-invoice-stamp/`, as the user asked. The phases are now in `plan.md`.
- 19 Nov 2026: Task 1 done (46b0295). Migrate added the 4 fields and ticked `Woqod Group` and `Woqod Group (G.W)` on sabaa.local. 4 tests pass.
- 19 Nov 2026: Task 2 done (fb9f080). 17 tests pass in `sabaa.sabaa.invoice_stamp.test_invoice_stamp`. Ruff check and format are clean on the new files.
- 19 Nov 2026: `test_flag_change_shows_on_next_print` saves the Customer Group as a document, like a desk save. The save clears the cache, so the test needs no explicit `clear_document_cache`.
- 19 Nov 2026: Phase 1 review (frappe-code-review): no defects. Accepted: `test_group_on_invoice_decides` uses any existing customer of another group. The rule reads only `doc.customer_group`, so the customer value does not change the result.
- 19 Nov 2026: The bench web server still runs `apps/sabaa`. After the Phase 2 migrate, the local desk cannot print "Sales Invoice - Custom" until `apps/sabaa` has this branch, because the server does not know `get_invoice_stamp_url`.
- 19 Nov 2026: Task 3 done (e7b7960). The print tests use the newest submitted Saba invoice on the site and move it to the test group inside the savepoint. On a site with no submitted invoice they skip. This avoids posting ledger entries in tests.
- 19 Nov 2026: Local PDF check with sample transparent stamps (`/files/sample-saba-stamp.png`, `/files/sample-gw-stamp.png`, set in App Settings on sabaa.local):
  - SIV/22622/2026 (Woqod Group, SIV series): red Saba stamp on the Authorized Signature line, centered.
  - GW/SIV/00228/2026 (Woqod Group (G.W), GW series): green Green World stamp, same place.
  - SIV/22648/2026 (Cash Customers): no stamp, page the same as before.
  - Woqod Group (the Saba group) also has GW series invoices, for example GW/SIV/00233/2026-1. They get the Green World stamp, as decided in Q5.
- 19 Nov 2026: Phase 2 review (frappe-code-review): escape the stamp URL in `src` with `| e` (0874c7b). Accepted: the Mobile App test calls the van_sales API in the same process and leaves `frappe.response` set. The next request resets it.
- 19 Nov 2026: All 20 tests pass (17 + 3).
- 19 Nov 2026: Phase 3 Steps 1, 2 and 5 done: 20 tests pass, ruff is clean on the new Python files, [user-guide.md](user-guide.md) written. Steps 4, 6, 7 and 8 (staging comparison, deploy, M1 to M6, PR ready) need the user.
- 19 Nov 2026: Moved from the worktree to `apps/sabaa`. All 20 tests pass from `apps/sabaa` without a `PYTHONPATH` override.
- 19 Nov 2026: The user found the stamp too large. In the browser print view (and the Mobile App, which shows the HTML on screen) Frappe's print CSS won: `img { max-width: 100% }` and the screen rule `td img { width: 100% !important }` stretched the stamp to 205x100 px. Fixed in d5f3704: selector `.print-format .sign-space img.sign-stamp` with `width/height: auto !important` and `max-width/max-height: 70px !important`, `bottom: -6px`. Checked GW/SIV/00228/2026 at 1280 px and 400 px widths (70x70) and as PDF. 20 tests pass.
- 19 Nov 2026: Local gunicorn does not serve `/files`, so images (also the company logo) do not load in the local browser print view. The check used a copy of the page with local file paths.
- 19 Nov 2026: Phase 3 Step 4: staging's "Sales Invoice - Custom" in the database (html, css, `modified` 2026-10-11 13:11:08) is the same as `upstream/develop`. The old file draft by "akwad" on staging matches the SO Remarks commit f555574.
- 19 Nov 2026: Draft deploy to staging (nameer-remote / sabaa.akwad.qa), label `woqod-invoice-stamp`, as the user asked: staging stays on `feat/customer-group-ledger-summary` @ 17e7667. The 8 code and test files are drafts next to the Customer Group Ledger Summary report (same deploy, so those 5 drafts now also carry this label). Checks before the deploy on the combined state: 17 + 3 stamp tests, 11 ledger summary tests, ruff clean. Outcome: applied, no overlaps, no backups. Staging needs `bench migrate` and `bench restart` by hand (0 post-remote hooks).
