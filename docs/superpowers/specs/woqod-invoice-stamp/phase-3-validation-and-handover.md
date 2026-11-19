# Phase 3: Validation and Handover

Read `plan-overview.md` and `test-plan.md` first.

### Task 4: Checks, staging and user guide

**Files:**
- Create: `docs/woqod-invoice-stamp-user-guide.md`
- Modify: `docs/superpowers/progress/woqod-invoice-stamp.md`

- [ ] **Step 1: Run all tests of the feature**

Run each module from `test-plan.md` section 3.
Expected: all pass (20 tests). Record the counts in the progress file.

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

Run M1 to M6 from `test-plan.md` section 5. Record the document names and the results in the progress file.

- [ ] **Step 8: Commit and mark the PR ready**

```bash
git add docs
git commit -m "docs(invoice-stamp): add the user guide and record the checks"
```

Update the PR description with the test results. Mark the PR ready for review only after the user agrees.
