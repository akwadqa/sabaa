# Phase 1: Fields and Stamp Rule

Read `plan-overview.md` (Global Constraints) and `design.md` sections 5 and 6 first.

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

`test_flag_change_shows_on_next_print` pins the cache: `frappe.db.set_value` does not clear the cache that `frappe.get_cached_value` reads, but a desk save does. If the test needs the explicit `clear_document_cache` to pass, keep it and note in the progress file that a desk save clears the cache.

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

- [ ] Run `frappe-code-review` on the Phase 1 diff. Fix the findings, or record each one you defer in the progress file.
- [ ] Update `docs/superpowers/progress/woqod-invoice-stamp.md`: status, commits, test counts.
