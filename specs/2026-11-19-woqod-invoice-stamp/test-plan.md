# Woqod Invoice Stamp: Test Plan

This plan lists every check for the feature. The phase files hold the test code. This file maps the tests to the decisions and adds the manual checks for staging.

## 1. How to run

- From `/home/work/saba-bench`, one module at a time: `bench --site sabaa.local run-tests --app sabaa --module <module>`. Do not use a full `--app` run.
- Tests use `FrappeTestCase` with a savepoint per test. No test commits.
- Test data: groups `_Test Stamp Group` (flagged) and `_Test No Stamp Group`. App Settings stamps `/files/saba-stamp.png` and `/files/gw-stamp.png`. Company `Saba Trading Group`.

## 2. Decision coverage

| Decision | Tests |
|---|---|
| Q1 both Woqod groups | `test_patch_ticks_existing_woqod_groups`, manual M1 |
| Q2 flag on Customer Group | `test_customer_group_has_stamp_flag`, `test_unflagged_group_gets_no_stamp`, `test_flag_change_shows_on_next_print` |
| Q3 group on the invoice | `test_group_on_invoice_decides` |
| Q4 stamp at print time | `test_print_shows_stamp_in_signature_box`, `test_mobile_html_has_absolute_stamp_url`, manual M2 to M4 |
| Q5 brand by naming series | `test_submitted_invoice_of_flagged_group_gets_saba_stamp`, `test_gw_series_gets_green_world_stamp`, `test_empty_series_uses_saba_stamp` |
| Q6 submitted invoices and returns | `test_submitted_return_gets_stamp`, `test_draft_and_cancelled_get_no_stamp` |
| Q7 Authorized Signature box | `test_print_shows_stamp_in_signature_box`, local PDF check, manual M2 |
| Q8 only Sales Invoice - Custom | Manual M5 |
| Q9 old invoices too | Manual M6 |
| Q10 images in App Settings | `test_app_settings_has_stamp_images_in_own_section`, `test_private_stamp_file_is_refused`, `test_public_stamp_file_is_accepted`, `test_missing_brand_image_gives_no_stamp` |
| Q11 no signature | No signature field exists. Reviewed in the diff. |

## 3. Automated tests per module

| Module | Count | Covers |
|---|---|---|
| `sabaa.sabaa.invoice_stamp.test_invoice_stamp` | 17 | Fields, Woqod patch, stamp rule, private file check, Jinja hook |
| `sabaa.sabaa.invoice_stamp.test_invoice_stamp_print` | 3 | Print format with and without stamp, Mobile App HTML |

Update the counts in this table when a phase ends.

## 4. Edge cases

| Case | Expected | Pinned by |
|---|---|---|
| Invoice group differs from the current customer group | The invoice group decides | `test_group_on_invoice_decides` |
| Brand image empty | No stamp, no error | `test_missing_brand_image_gives_no_stamp`, `test_print_without_stamp_keeps_signature_box` |
| Private stamp file | Save refused, message names the field | `test_private_stamp_file_is_refused` |
| Empty `customer_group` | No stamp | `test_invoice_without_group_gives_no_stamp` |
| Empty `naming_series` | Saba stamp | `test_empty_series_uses_saba_stamp` |
| Woqod group missing on a site | Patch runs, ticks the other group | `test_patch_skips_missing_group` |
| Flag cleared on a group | Next print has no stamp | `test_flag_change_shows_on_next_print` |

## 5. Manual checks (staging, Phase 3)

Upload the client's stamp images first. Record document names in [progress.md](progress.md).

| ID | Steps | Expected |
|---|---|---|
| M1 | Open Customer Group `Woqod Group` and `Woqod Group (G.W)`. | "Print Stamp on Invoice" is ticked on both. |
| M2 | Desk: print a submitted `Woqod Group` invoice (SIV) and a `Woqod Group (G.W)` invoice (GW). Download both PDFs. | Saba stamp on the first, Green World stamp on the second, in the Authorized Signature box. |
| M3 | Email the SIV invoice to a test address from the desk. | The PDF attachment has the stamp. |
| M4 | Mobile App: open and share a Woqod invoice. | The shared invoice has the stamp. |
| M5 | Print a Woqod invoice with another format, for example "Sales Invoice Return". Print a Lulu invoice with "Sales Invoice - Custom". | No stamp on either. |
| M6 | Print a Woqod invoice from May 2026 and a draft Woqod invoice. | Stamp on the May invoice. No stamp on the draft. |
