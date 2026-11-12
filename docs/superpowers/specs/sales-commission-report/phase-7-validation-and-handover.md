# Sales Commission Report – Phase 7: Validation and handover

> Read `plan-overview.md` first: it holds the global constraints, review focus and file map that apply to every task here.

### Task 13: Validation on real data and handover docs

**Files:** Create `docs/commission-configuration-guide.md` (for the client admin, technical-writing style), `docs/superpowers/progress/sales-commission-v2.md` (validation results).

- [ ] **Step 1:** Run full suite: `bench --site sabaa.local run-tests --app sabaa --module sabaa.sabaa.commission.tests` plus each DocType and report test. Expect all PASS. Record counts.
- [ ] **Step 2:** On `sabaa.local`: create the default plan, set Commission Settings (`erpnext_start_date` 2026-05-01, delivery charge account `4203 - Delivery Charges`), run the report for May and June 2026 (Month and Q2 Quarter, both views), export to Excel, and time each run (must finish under the report timeout).
- [ ] **Step 3:** Compare May/June totals per category with the commission expense account balances; write each difference and its cause (open question, missing setup, or bug) in the progress file. Fix any bug found with a regression test first.
- [ ] **Step 4:** Write the admin guide: first setup, monthly routine (Check setup → report → run → approve → mark paid), new period, answering an open question (which field to change for each code G1–U1).
- [ ] **Step 5:** Run `frappe-code-review` skill on the branch diff; fix findings.
- [ ] **Step 6: Commit** — `docs(commission): add admin guide and validation results`
