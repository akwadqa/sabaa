# Phase 2: Print Format

Read `plan-overview.md` (Global Constraints) and `design.md` section 6.3 first.

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

Expected: the Saba and Green World stamps sit on the Authorized Signature line, about 100 px, and the company name stays readable. The other invoice looks the same as before. Save screenshots and record the invoice names in the progress file.

- [ ] **Step 6: Commit**

```bash
git add sabaa/sabaa/print_format/sales_invoice___custom sabaa/sabaa/invoice_stamp/test_invoice_stamp_print.py
git commit -m "feat(invoice-stamp): print the stamp in the Sales Invoice signature box"
```

### Phase 2 close

- [ ] Run `frappe-code-review` on the Phase 2 diff. Fix the findings, or record each one you defer in the progress file.
- [ ] Update the progress file.
