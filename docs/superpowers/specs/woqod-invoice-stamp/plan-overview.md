# Woqod Invoice Stamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Submitted Sales Invoices of customer groups with "Print Stamp on Invoice" ticked print the stamp of their brand in the "Authorized Signature" box.

**Architecture:** A sabaa patch adds a check field to Customer Group and two stamp image fields to App Settings. A Jinja method `get_invoice_stamp_url(doc)` decides the stamp for an invoice. The print format "Sales Invoice - Custom" calls it, so desk print, email, PDF and the Mobile App get the stamp from one place.

**Tech Stack:** Frappe 15 / ERPNext 15, Python 3.10+, Jinja print format.

**Spec:** `docs/superpowers/specs/woqod-invoice-stamp/design.md` (read it with this plan). Test plan: `test-plan.md` in this folder.

**Phase files:** `phase-1-fields-and-rule.md`, `phase-2-print-format.md`, `phase-3-validation-and-handover.md` in this folder. Progress: `docs/superpowers/progress/woqod-invoice-stamp.md`.

## Global Constraints

- App `sabaa`, module `Sabaa`, branch `feat/woqod-invoice-stamp`, worktree `/home/work/saba-bench/sabaa-invoice-stamp`.
- `apps/sabaa` has uncommitted work on `feat/customer-group-ledger-summary`. Before the first test, ask the user how the bench loads this branch. Do not change `apps/sabaa` without asking.
- Ruff config in `pyproject.toml`: tabs, double quotes, line length 110, target `py310`.
- No fixtures. Custom fields come from a patch with `create_custom_fields(..., ignore_validate=True, update=True)` and `"module": "Sabaa"`.
- No changes in the van_sales app.
- No `frappe.db.commit()` / `frappe.db.rollback()` in app code. The new patches do not commit.
- Exact names: `custom_print_stamp_on_invoice`, `custom_invoice_stamp_section`, `custom_saba_invoice_stamp`, `custom_green_world_invoice_stamp`, `get_invoice_stamp_url`, `validate_stamp_files`, `InvoiceStamp`, `InvoiceStampError`.
- Woqod group names, exactly: `Woqod Group` and `Woqod Group (G.W)`.
- Green World rule: `naming_series` starts with `GW`.
- Tests run from `/home/work/saba-bench`: `bench --site sabaa.local run-tests --app sabaa --module <dotted module>`. Use `FrappeTestCase` with a savepoint per test, as in `sabaa/sabaa/doctype/purchase_analysis_settings/test_purchase_analysis_settings.py`.
- If the site says "Testing is disabled", stop and ask the user before `bench --site sabaa.local set-config allow_tests true`.
- After a patch or print format JSON change: `bench --site sabaa.local migrate`.
- Commits: Conventional Commits with scope `invoice-stamp`, for example `feat(invoice-stamp): ...`. No AI co-author line.
- Run `frappe-code-review` before you mark a phase done. Update the progress file at the end of each task.

## File Structure

| File | Responsibility |
|---|---|
| `sabaa/patches/add_invoice_stamp_fields.py` | Custom fields on Customer Group and App Settings |
| `sabaa/patches/enable_invoice_stamp_for_woqod_groups.py` | Tick the flag on the two Woqod groups |
| `sabaa/patches.txt` | Register both patches in `[post_model_sync]` |
| `sabaa/sabaa/invoice_stamp/__init__.py` | `InvoiceStamp`, `get_invoice_stamp_url`, `validate_stamp_files`, `InvoiceStampError` |
| `sabaa/sabaa/invoice_stamp/test_invoice_stamp.py` | Tests for the rule, the validation and the patches |
| `sabaa/sabaa/invoice_stamp/test_invoice_stamp_print.py` | Tests that render the print format |
| `sabaa/hooks.py` | Jinja method and App Settings `validate` hook |
| `sabaa/sabaa/print_format/sales_invoice___custom/sales_invoice___custom.json` | Stamp image in the signature box |
| `docs/woqod-invoice-stamp-user-guide.md` | Short guide for administrators |

## Review Focus

1. An invoice for a Woqod customer that later moved to another group. The stamp follows the group on the invoice. Pinned by `test_group_on_invoice_decides` in Task 2.
2. A submitted invoice whose brand image is empty, for example only the Saba stamp is uploaded and the invoice is `GW`. It prints without a stamp and without an error. Pinned by `test_missing_brand_image_gives_no_stamp` in Task 2 and `test_print_without_stamp_keeps_signature_box` in Task 3.
3. An administrator uploads a stamp as a private file. Save is refused with a clear message, because the Mobile App cannot show it. Pinned by `test_private_stamp_file_is_refused` in Task 2.
4. An invoice with an empty `customer_group` or `naming_series` (old or imported data). No error, no stamp or the Saba stamp. Pinned by `test_invoice_without_group_gives_no_stamp` and `test_empty_series_uses_saba_stamp` in Task 2.
5. The Mobile App HTML for a stamped invoice has an absolute image URL. Pinned by `test_mobile_html_has_absolute_stamp_url` in Task 3.

## Phases

| Phase | File | Tasks | Outcome |
|---|---|---|---|
| 1 | `phase-1-fields-and-rule.md` | 1, 2 | Fields, Woqod flags, stamp rule, validation, hooks |
| 2 | `phase-2-print-format.md` | 3 | Stamp in "Sales Invoice - Custom", local PDF check |
| 3 | `phase-3-validation-and-handover.md` | 4 | Lint, branch review, staging checks, user guide |
