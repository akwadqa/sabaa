# Woqod Invoice Stamp Implementation Plan

Steps use checkboxes (`- [ ]`). Tick each step when it is done.

**Goal:** Submitted Sales Invoices of customer groups with "Print Stamp on Invoice" ticked print the stamp of their brand in the "Authorized Signature" box.

**Architecture:** A sabaa patch adds a check field to Customer Group and two stamp image fields to App Settings. A Jinja method `get_invoice_stamp_url(doc)` decides the stamp for an invoice. The print format "Sales Invoice - Custom" calls it, so desk print, email, PDF and the Mobile App get the stamp from one place.

**Tech Stack:** Frappe 15 / ERPNext 15, Python 3.10+, Jinja print format.

**Spec:** [design.md](design.md) · **Tests:** [test-plan.md](test-plan.md) · **Progress:** [progress.md](progress.md)

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
- Run `frappe-code-review` before you mark a phase done. Update [progress.md](progress.md) at the end of each task.

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
| `specs/2026-11-19-woqod-invoice-stamp/user-guide.md` | Short guide for administrators |

## Review Focus

1. An invoice for a Woqod customer that later moved to another group. The stamp follows the group on the invoice. Pinned by `test_group_on_invoice_decides` in Task 2.
2. A submitted invoice whose brand image is empty, for example only the Saba stamp is uploaded and the invoice is `GW`. It prints without a stamp and without an error. Pinned by `test_missing_brand_image_gives_no_stamp` in Task 2 and `test_print_without_stamp_keeps_signature_box` in Task 3.
3. An administrator uploads a stamp as a private file. Save is refused with a clear message, because the Mobile App cannot show it. Pinned by `test_private_stamp_file_is_refused` in Task 2.
4. An invoice with an empty `customer_group` or `naming_series` (old or imported data). No error, no stamp or the Saba stamp. Pinned by `test_invoice_without_group_gives_no_stamp` and `test_empty_series_uses_saba_stamp` in Task 2.
5. The Mobile App HTML for a stamped invoice has an absolute image URL. Pinned by `test_mobile_html_has_absolute_stamp_url` in Task 3.

## Phases

| Phase | Tasks | Outcome |
|---|---|---|
| 1 | 1, 2 | Fields, Woqod flags, stamp rule, validation, hooks |
| 2 | 3 | Stamp in "Sales Invoice - Custom", local PDF check |
| 3 | 4 | Lint, branch review, staging checks, user guide |

---

## Phase 1: Fields and Stamp Rule

### Task 1: Custom fields and the Woqod flags

**Files:**
- Create: `sabaa/patches/add_invoice_stamp_fields.py`
- Create: `sabaa/patches/enable_invoice_stamp_for_woqod_groups.py`
- Modify: `sabaa/patches.txt` (add both to the end of `[post_model_sync]`, the field patch first)
- Create: `sabaa/sabaa/invoice_stamp/__init__.py` (empty in this task)
- Create: `sabaa/sabaa/invoice_stamp/test_invoice_stamp.py`

**Interfaces:**
- Produces: the four fields in `design.md` 5. Patch modules with `execute()`.
- Produces in `enable_invoice_stamp_for_woqod_groups`: `WOQOD_GROUPS = ("Woqod Group", "Woqod Group (G.W)")`.

- [ ] **Step 1: Write the failing tests**

```python
class TestInvoiceStampSchema(FrappeTestCase):
	def test_customer_group_has_stamp_flag(self):
		field = frappe.get_meta("Customer Group").get_field("custom_print_stamp_on_invoice")
		self.assertEqual(field.fieldtype, "Check")

	def test_app_settings_has_stamp_images_in_own_section(self):
		meta = frappe.get_meta("App Settings")
		self.assertEqual(meta.get_field("custom_invoice_stamp_section").fieldtype, "Section Break")
		for fieldname in ("custom_saba_invoice_stamp", "custom_green_world_invoice_stamp"):
			self.assertEqual(meta.get_field(fieldname).fieldtype, "Attach Image")


class TestEnableWoqodGroups(FrappeTestCase):
	# savepoint setUp / rollback cleanup as in test_purchase_analysis_settings.py

	def test_patch_ticks_existing_woqod_groups(self):
		for name in WOQOD_GROUPS:
			make_customer_group(name)  # get or create, flag 0
		execute()
		for name in WOQOD_GROUPS:
			self.assertEqual(frappe.db.get_value("Customer Group", name, "custom_print_stamp_on_invoice"), 1)

	def test_patch_skips_missing_group(self):
		make_customer_group("Woqod Group")  # get or create, flag 0
		with patch(f"{PATCH_MODULE}.WOQOD_GROUPS", ("Woqod Group", "_Test Missing Group")):
			execute()
		self.assertEqual(frappe.db.get_value("Customer Group", "Woqod Group", "custom_print_stamp_on_invoice"), 1)
```

`PATCH_MODULE` is `"sabaa.patches.enable_invoice_stamp_for_woqod_groups"`. `patch` is `unittest.mock.patch`. Do not delete real groups in a test, because customers use them.

- [ ] **Step 2: Run the tests to make sure they fail**

Run: `bench --site sabaa.local run-tests --app sabaa --module sabaa.sabaa.invoice_stamp.test_invoice_stamp`
Expected: FAIL. The fields and the patch module do not exist.

- [ ] **Step 3: Write the two patches and register them**

Use the fields, labels and descriptions from `design.md` 5. The flag patch uses `frappe.db.exists` and `frappe.db.set_value` per group.

- [ ] **Step 4: Migrate and run the tests to make sure they pass**

Run: `bench --site sabaa.local migrate`, then the command from Step 2. Expected: PASS (4 tests). Check in the desk that App Settings shows the "Invoice Stamp" section after "Print Formats".

- [ ] **Step 5: Commit**

```bash
git add sabaa/patches sabaa/patches.txt sabaa/sabaa/invoice_stamp
git commit -m "feat(invoice-stamp): add stamp fields and tick the Woqod groups"
```

### Task 2: Stamp rule, App Settings validation and hooks

**Files:**
- Modify: `sabaa/sabaa/invoice_stamp/__init__.py`
- Modify: `sabaa/hooks.py` (`jinja["methods"]` and `doc_events`)
- Modify: `sabaa/sabaa/invoice_stamp/test_invoice_stamp.py`

**Interfaces:**
- Consumes: the fields from Task 1.
- Produces in `sabaa.sabaa.invoice_stamp`:
  - `GREEN_WORLD_SERIES_PREFIX = "GW"`
  - `class InvoiceStampError(frappe.ValidationError)`
  - `class InvoiceStamp: __init__(self, doc)`, properties `is_due -> bool`, `is_green_world -> bool`, `url -> str | None`
  - `get_invoice_stamp_url(doc) -> str | None`
  - `validate_stamp_files(doc, method=None) -> None`

- [ ] **Step 1: Write the failing tests**

Test data: a flagged group `_Test Stamp Group` and an unflagged group `_Test No Stamp Group`. App Settings stamps set with `frappe.db.set_single_value` to `/files/saba-stamp.png` and `/files/gw-stamp.png`. Invoices are unsaved `frappe.get_doc({"doctype": "Sales Invoice", ...})` objects with `customer_group`, `naming_series` and `docstatus` set. Clear the document cache of App Settings in cleanup.

```python
class TestInvoiceStampRule(FrappeTestCase):
	def test_submitted_invoice_of_flagged_group_gets_saba_stamp(self):
		self.assertEqual(get_invoice_stamp_url(self.invoice(series="SIV/.#")), SABA_URL)

	def test_gw_series_gets_green_world_stamp(self):
		self.assertEqual(get_invoice_stamp_url(self.invoice(series="GW/SIV/.#")), GW_URL)

	def test_empty_series_uses_saba_stamp(self):
		self.assertEqual(get_invoice_stamp_url(self.invoice(series=None)), SABA_URL)

	def test_submitted_return_gets_stamp(self):
		self.assertEqual(get_invoice_stamp_url(self.invoice(is_return=1)), SABA_URL)

	def test_draft_and_cancelled_get_no_stamp(self):
		self.assertIsNone(get_invoice_stamp_url(self.invoice(docstatus=0)))
		self.assertIsNone(get_invoice_stamp_url(self.invoice(docstatus=2)))

	def test_unflagged_group_gets_no_stamp(self):
		self.assertIsNone(get_invoice_stamp_url(self.invoice(group="_Test No Stamp Group")))

	def test_invoice_without_group_gives_no_stamp(self):
		self.assertIsNone(get_invoice_stamp_url(self.invoice(group=None)))

	def test_missing_brand_image_gives_no_stamp(self):
		frappe.db.set_single_value("App Settings", "custom_green_world_invoice_stamp", None)
		self.assertIsNone(get_invoice_stamp_url(self.invoice(series="GW/SIV/.#")))

	def test_group_on_invoice_decides(self):
		# customer's current group is unflagged; the invoice keeps the flagged group
		self.assertEqual(get_invoice_stamp_url(self.invoice(customer=unflagged_customer)), SABA_URL)

	def test_flag_change_shows_on_next_print(self):
		frappe.db.set_value("Customer Group", "_Test Stamp Group", "custom_print_stamp_on_invoice", 0)
		frappe.clear_document_cache("Customer Group", "_Test Stamp Group")
		self.assertIsNone(get_invoice_stamp_url(self.invoice()))


class TestStampFileValidation(FrappeTestCase):
	def test_private_stamp_file_is_refused(self):
		settings = frappe.get_single("App Settings")
		settings.custom_saba_invoice_stamp = "/private/files/saba-stamp.png"
		with self.assertRaisesRegex(InvoiceStampError, "Saba Stamp"):
			settings.save()

	def test_public_stamp_file_is_accepted(self):
		settings = frappe.get_single("App Settings")
		settings.custom_saba_invoice_stamp = "/files/saba-stamp.png"
		settings.save()

	def test_jinja_method_is_registered(self):
		self.assertIn("sabaa.sabaa.invoice_stamp.get_invoice_stamp_url", frappe.get_hooks("jinja")["methods"])
```

`test_flag_change_shows_on_next_print` pins the cache: `frappe.db.set_value` does not clear the cache that `frappe.get_cached_value` reads, but a desk save does. If the test needs the explicit `clear_document_cache` to pass, keep it and note in [progress.md](progress.md) that a desk save clears the cache.

- [ ] **Step 2: Run the tests to make sure they fail**

Run: `bench --site sabaa.local run-tests --app sabaa --module sabaa.sabaa.invoice_stamp.test_invoice_stamp`
Expected: FAIL with an import error for `get_invoice_stamp_url`.

- [ ] **Step 3: Write `InvoiceStamp`, `get_invoice_stamp_url` and `validate_stamp_files`, and add both hooks**

Follow `design.md` 6.1 and 6.2. `url` reads the brand image with `frappe.db.get_single_value("App Settings", fieldname)`. `validate_stamp_files` uses the field label from `doc.meta.get_label(fieldname)` in the message. Raise with `frappe.throw(msg, exc=InvoiceStampError)`.

- [ ] **Step 4: Run the tests to make sure they pass**

Run: the command from Step 2. Expected: PASS (17 tests in the module).

- [ ] **Step 5: Commit**

```bash
git add sabaa/sabaa/invoice_stamp sabaa/hooks.py
git commit -m "feat(invoice-stamp): decide the stamp per invoice and refuse private stamp files"
```

### Phase 1 close

- [ ] Run `frappe-code-review` on the Phase 1 diff. Fix the findings, or record each one you defer in [progress.md](progress.md).
- [ ] Update [progress.md](progress.md): status, commits, test counts.

---

## Phase 2: Print Format

### Task 3: Stamp in "Sales Invoice - Custom"

**Files:**
- Modify: `sabaa/sabaa/print_format/sales_invoice___custom/sales_invoice___custom.json` (`html`, `css` and `modified`)
- Create: `sabaa/sabaa/invoice_stamp/test_invoice_stamp_print.py`

**Interfaces:**
- Consumes: `get_invoice_stamp_url(doc)` from Task 2 (Jinja method).
- Produces: CSS class `sign-stamp`. The stamp `<img>` has `alt="Company stamp"`.

- [ ] **Step 1: Write the failing tests**

Render with `frappe.get_print("Sales Invoice", doc.name, print_format="Sales Invoice - Custom", doc=doc)`. Use a submitted Sales Invoice made in the test (company `Saba Trading Group`, one item, `customer_group` set). Reuse the setup of Task 2 for the groups and the App Settings images.

```python
class TestInvoiceStampPrint(FrappeTestCase):
	def test_print_shows_stamp_in_signature_box(self):
		html = self.render(self.submitted_invoice(group="_Test Stamp Group"))
		self.assertIn('class="sign-stamp"', html)
		self.assertIn(SABA_URL, html)

	def test_print_without_stamp_keeps_signature_box(self):
		html = self.render(self.submitted_invoice(group="_Test No Stamp Group"))
		self.assertNotIn('class="sign-stamp"', html)
		self.assertIn("Authorized Signature", html)

	def test_mobile_html_has_absolute_stamp_url(self):
		response = get_document_html("Sales Invoice", invoice.name)  # van_sales API
		self.assertIn(get_url() + SABA_URL, response["data"]["html"])
```

Check the shape that `gen_response` returns in `van_sales/van_sales/van_sales/api/utils.py` before you write the last assertion.

- [ ] **Step 2: Run the tests to make sure they fail**

Run: `bench --site sabaa.local run-tests --app sabaa --module sabaa.sabaa.invoice_stamp.test_invoice_stamp_print`
Expected: FAIL. The format has no stamp yet.

- [ ] **Step 3: Change the print format**

Edit the `html` and `css` strings in the JSON. Keep every other line of the template the same.

```jinja
{% set stamp_url = get_invoice_stamp_url(doc) %}
...
<td class="sign-box">
  <div class="sign-title">{{ company_name }}</div>
  <div class="sign-space">
    {% if stamp_url %}<img src="{{ stamp_url }}" class="sign-stamp" alt="Company stamp">{% endif %}
  </div>
  <div class="sign-label">Authorized Signature</div>
</td>
```

Add the CSS from `design.md` 6.3. Set `modified` to the current time.

- [ ] **Step 4: Migrate and run the tests to make sure they pass**

Run: `bench --site sabaa.local migrate`, then the command from Step 2. Expected: PASS (3 tests).

- [ ] **Step 5: Check a real PDF locally**

1. Upload a sample transparent PNG as the Saba stamp and as the Green World stamp in App Settings.
2. Open one submitted invoice of `Woqod Group` (SIV series) and one of `Woqod Group (G.W)` (GW series). Use Print, then PDF.
3. Open one invoice of another group.

Expected: the Saba and Green World stamps sit on the Authorized Signature line, about 100 px, and the company name stays readable. The other invoice looks the same as before. Save screenshots and record the invoice names in [progress.md](progress.md).

- [ ] **Step 6: Commit**

```bash
git add sabaa/sabaa/print_format/sales_invoice___custom sabaa/sabaa/invoice_stamp/test_invoice_stamp_print.py
git commit -m "feat(invoice-stamp): print the stamp in the Sales Invoice signature box"
```

### Phase 2 close

- [ ] Run `frappe-code-review` on the Phase 2 diff. Fix the findings, or record each one you defer in [progress.md](progress.md).
- [ ] Update [progress.md](progress.md).

---

## Phase 3: Validation and Handover

### Task 4: Checks, staging and user guide

**Files:**
- Create: `specs/2026-11-19-woqod-invoice-stamp/user-guide.md`
- Modify: `specs/2026-11-19-woqod-invoice-stamp/progress.md`

- [ ] **Step 1: Run all tests of the feature**

Run each module from [test-plan.md](test-plan.md) section 3.
Expected: all pass (20 tests). Record the counts in [progress.md](progress.md).

- [ ] **Step 2: Lint the changed files**

Run: `ruff check` and `ruff format --check` on the changed Python files.
Expected: no findings in the new files. Do not reformat files that this branch does not change.

- [ ] **Step 3: Review the whole branch**

Run `frappe-code-review` on `git diff upstream/develop...HEAD`. Fix the findings in one wave and run Steps 1 and 2 again.

- [ ] **Step 4: Compare the print format on staging with the repo version**

Get the `html` of "Sales Invoice - Custom" from staging. Compare it with the repo version on `upstream/develop`.
Expected: no difference. If there is a difference, stop and ask the user which version to keep.

- [ ] **Step 5: Write the user guide**

Use the `technical-writing` skill. Cover:
1. Upload the two stamps in App Settings → Invoice Stamp (transparent PNG, public file).
2. Tick or clear "Print Stamp on Invoice" on a customer group.
3. Which invoices get the stamp (submitted invoices and returns, by the group on the invoice, brand by naming series).
4. What happens without an image.

- [ ] **Step 6: Push and deploy to staging**

Push the branch and deploy with the staging deploy skill. Staging needs `bench migrate`. Ask the user for the steps that need their access.

- [ ] **Step 7: Manual checks on staging**

Run M1 to M6 from [test-plan.md](test-plan.md) section 5. Record the document names and the results in [progress.md](progress.md).

- [ ] **Step 8: Commit and mark the PR ready**

```bash
git add specs
git commit -m "docs(invoice-stamp): add the user guide and record the checks"
```

Update the PR description with the test results. Mark the PR ready for review only after the user agrees.
