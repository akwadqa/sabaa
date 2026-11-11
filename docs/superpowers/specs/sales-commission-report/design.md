# Sales Commission & Incentive — Design (fresh rebuild)

Date: 2026-11-11 · App: `sabaa` (module Sabaa) · Frappe/ERPNext 15
Location: `docs/superpowers/specs/sales-commission-report/design.md`
on a new branch, and the next step is `superpowers:writing-plans`.

## 0. Branch and starting point

- New local branch `feat/sales-commission-v2` from `develop` (`49b4081`). It does **not** contain the 40 commits of
  `feat/sales-commission-report`. Nothing from that branch is reused as code.
- Uncommitted work on the old branch (`qa-review.md`, `run_cache.py`, two modified docs) stays on the old branch
  (`git stash -u` before switching, so it is not lost and does not leak into the new branch).
- The local site `sabaa.local` has the old Commission DocTypes in its database from the old branch. The builder
  drops them on the dev site before migrating the new branch (dev site only; production never had them).

## 1. Intent

Saba Trading Group pays commissions to sales, logistics and online staff under an approved commission map.
Accounts calculates them outside ERPNext today. The goal is one ERPNext report that calculates every category
automatically from **configurable** rules, shows team totals and the per-employee breakdown, exports to Excel,
and an approval document that locks a paid period.

## 2. Goals, non-goals, anti-goals

Goals
- One Script Report, **Sales Commission & Incentive**, for all six categories: Traditional Trade, Modern Trade,
  Sales Management, Smile24, Logistics, Tenders.
- Every tier, threshold, amount, percentage, headcount base, customer group, recipient and split is data.
  Code owns only the building blocks (basis, period, tier method, recipients, split).
- Rules are **versioned**: a plan has valid-from/valid-to dates. A new map is a new plan, not new code.
- Monthly, quarterly-average and rolling-three-month-average periods, chosen per rule.
- Team and individual commissions, with automatic distribution.
- Every row shows how it was reached: basis, period values, target (after scaling), tier, fixed part, excess part,
  share, amount.
- A **Commission Run** saves and approves a period's results so paid figures stay fixed.

Non-goals
- Posting the journal entry or salary component (accounts books from the approved run, as today).
- Changing how invoices, payments or journal entries are recorded.

Anti-goals
- Silent zeros. Missing setup, missing data or an unanswered business rule shows a status
  ("Waiting for business input", "Missing data", "Not assigned"), never 0.
- Duplicated team data that drifts from HR (see 6.3).

## 3. Facts from the site (sabaa.local, production copy)

- Invoices exist from 2 May 2026 (9,109 submitted to 26 Oct). Jan–Apr exist only as an opening journal entry.
- Customer groups: `Cash Customers` (5,828 inv) = Traditional Trade; hypermarket chain groups under
  `Hypermarket customers` (incl. `(G.W)` Green World groups) = Modern Trade; `Online Sales` (170) = Smile24;
  `Direct Sales` (16) excluded everywhere; `Van Sales` (605) and `Horeca Customers` (97) exist but are not in the map.
- Cash-customer collections: Journal Entries (allocated to invoices 560k; **unallocated 248k**),
  POS payments on the invoice (604k), Payment Entries (5k). Credit notes are also JEs to the customer and are
  not collections. `develop` has a `Sales Collection Account` child table listing the accounts that count as
  collections — reuse it.
- Customers carry **no** Sales Team rows; every invoice has one Sales Team row at 100%.
- Sales Person tree: `Cash Market Salesman Sales` (15 leaves) and `Hypermarket Sales Executive Sales` (15 leaves).
  They also hold the Sales Head, supervisors, a driver, a labor and a merchandiser; 10 leaves have no employee.
- Designations: Salesman 11, Sales Executive 8, Sales Supervisor 3, Sales Head 1, Sales Manager 1,
  Sales Coordinator 1, Delivery Driver 8 active (one is "Testing Employee"), labor 3 in Sales + 12 in Inventory.
- `reports_to` points every sales person to the Sales Head — it cannot give supervisor teams.
- Nothing on the site records: supervisor → salesmen, cashier assistant → salesman, hypermarket shares,
  tender recipients, tender invoices. Employee Group is empty; van_sales `Trip` only links salesman↔driver (20 rows).
- Smile24: all 170 invoices carry sales person Mohammed Irfan; delivery charge is an item/charge row to
  `4203 - Delivery Charges`; invoices carry the custom `driver` (Link Driver). Most Driver records have no employee.
- Tea Milk is item `MR-MILK-00014`, sold in Ctn and Pcs (48 per carton).

## 4. Constraints

- No fixtures; no `frappe.db.commit()`; ORM / query builder over raw SQL.
- Status = one Select field `status`, transitions enforced server-side. No Workflow DocType.
- Business logic in a Python package, exposed through whitelisted APIs; JS only for presentation.
- A half-year run (~30k invoices, ~40k ledger rows) must finish within the report timeout: set-based queries,
  one read per source per period, no per-invoice queries.

## 5. Approaches (decided)

1. **Composable rules — chosen by the user.** Code provides fixed building blocks; each rule picks a basis,
   period, tier method, recipient source and split, and holds its own numbers. A new map, or a new mix of
   existing blocks, needs no developer. Cost: a richer setup form, mitigated by a seeded default plan and a
   pre-run setup check.
2. One coded calculator per category with editable numbers. Simpler, but a change in a rule's shape needs code.
   Rejected: versioned maps make shape changes likely.
3. ERPNext Sales Person targets / commission rate. Dropped: no tiers, excess %, averages or pools.

User constraint on the choice: *commission rules and tiers configurable rather than hardcoded wherever possible.*

## 6. Design

### 6.1 DocTypes (module Sabaa, all prefixed "Commission" — no conflict with ERPNext/HRMS names)

**Commission Plan** — a versioned rule set.
`plan_name`, `company`, `valid_from`, `valid_to`, `status` (Draft / Active / Closed),
`excluded_customer_groups` (Table MultiSelect, default `Direct Sales`).
Server rule: two Active plans of the same company must not overlap in dates. A button
"Copy to new plan" duplicates the plan with its rules.

**Commission Rule** — one per category × role (standalone, because it has its own child tables).

| Field | Type | Purpose |
|---|---|---|
| plan | Link Commission Plan | |
| rule_name, category, role_label | Data / Select / Data | Category: the six categories |
| basis | Select | Collected Sales · Net Invoiced Sales · Company Sales · Delivery Fees · Unit Count · Tender Collections · Paired Basis |
| basis_sources | Table: Commission Basis Source | customer group + measure (Collected / Invoiced), descendants included. Company Sales = sum of rows, so cash collections + hypermarket invoiced (Sales Mgmt) and "all except Smile24" (Logistics) are both data |
| attribute_by | Select | Invoice Sales Person · Invoice Driver · None (company/pool) |
| period_mode | Select | Monthly · Quarterly Average · Rolling 3-Month Average. The average (total ÷ 3, not the total) only selects the tier and the excess base |
| payout_multiplier | Int | default 1: the tier amount is paid once per payout. Set 3 if the business confirms the amount is monthly and paid for a whole quarter (open question G4) |
| tier_method | Select | Fixed Step (amount of highest tier reached; last tier may add excess %) · Fixed + Excess % · Flat Rate |
| tiers | Table: Commission Tier | `threshold`, `fixed_amount`, `excess_percent` |
| flat_rate_percent | Percent | Tenders 1.5%, Smile24 delivery 50% |
| unit_rates | Table: Commission Unit Rate | item, UOM, amount per unit; the items are removed from the basis of other rules in the plan (Tea Milk) |
| bonus_after_count / bonus_per_unit | Int / Currency | Smile24 drivers: 5 QAR per free-delivery order beyond 100 |
| headcount_base | Int | 8 for supervisor and logistics; 0 = no scaling |
| headcount_counts | Select | Team Members · Recipients of share "Drivers" (etc.) |
| scale_amounts | Check | default off: only **targets** scale by actual ÷ base; amounts stay (user-confirmed for Logistics) |
| recipient_source | Select | Each Attributed Person · Supervisor of Sales Person Group · Pool |
| team_group | Link Sales Person (group) | members = enabled leaves under it in the period |
| member_designations | Table MultiSelect Designation | filters tree members (e.g. Salesman, Sales Executive) |
| paired_rule | Link Commission Rule | Cashier Assistant uses the paired salesman's basis and target |
| shares | Table: Commission Share | `share_name`, `percent`, `designation`, `department` (optional), `split` (Equal / By Assignment %) — e.g. Drivers 60 / Workers 40; Manager 60 / Assistant 40; Sales 40 / Management 60 |
| status_note | Small Text | shown in the report while a rule waits for business input |
| is_waiting_for_business | Check | report shows "Waiting for business input" instead of amounts |

**Commission Assignment** — the only hand-kept people data, dated. Holds what the site does not.
`plan` (optional), `rule` (optional), `employee`, `assignment_type`
(Assistant Of · Pool Share % · Share Member · Exclude · Include), `target_sales_person` / `target_employee`,
`percent`, `from_date`, `to_date`. Examples: cashier assistant pairs; hypermarket distribution plan
(a new row with a later `from_date` changes it); tender Sales/Management recipients; excluding a test employee.

**Commission Manual Figure** — monthly amounts for months ERPNext does not hold (March, April 2026).
`month` (first day), `rule` or `basis_key`, `sales_person` (optional), `amount`, `source_note`.
A period that needs a missing month and has no manual figure → row status "Missing data".

**Commission Run** (submittable) — locks a period.
`plan`, `company`, `period_type` (Month / Quarter), `period_start`, `period_end`,
`status` (Draft · Calculated · Approved · Paid · Cancelled), child **Commission Run Line** (same columns as the
report Detail view). Server-enforced transitions: Draft→Calculated (Calculate button, rerunnable),
Calculated→Approved (submit), Approved→Paid (action, with JE reference optional), Approved/Paid→Cancelled (cancel).
Only one non-cancelled run per plan + month. The report shows a banner when an approved run exists for the
period and the live total differs from it.
*My call — runs are always monthly.* A Quarterly Average rule produces lines only in the run for the last month
of its quarter; a Rolling rule produces lines every month; Monthly rules every month. This means a quarter is
never paid twice, and no Month run overlaps a Quarter run.
*My call — what a paid period locks.* The run's lines are the record of what was paid. While a plan has an
Approved or Paid run, its rules' tiers, shares and basis cannot be edited (server validation); a change needs
"Copy to new plan". Assignments and Manual Figures dated inside an Approved/Paid month cannot be edited or deleted.

**Settings** — reuse `Sales Collection Account` for collection accounts. New single **Commission Settings**:
`smile24_customer_group`, `delivery_charge_account`, `carton_uom`, default company,
`count_opening_balance_collections` (Check, default on: payments that settle the pre-ERPNext opening balance
count as collected sales, attributed to the customer's most recent invoice's sales person and flagged
"opening balance"; open question G5).

**Custom field** (created by a patch with `create_custom_fields`, not fixtures): `Sales Invoice.is_tender`
(Check, allow on submit = no). Tender = invoice with this ticked (my call; see open question T1).

### 6.2 Engine (`sabaa/commission/`, plain Python, no Desk dependency)

- `sources.py` — one set-based reader per measure, per period range:
  *Collected*: Payment Ledger Entries against customers of the basis groups, `voucher_type` Payment Entry or
  Journal Entry whose account side is in `Sales Collection Account`, plus POS `paid_amount`; excludes credit notes,
  opening entries, cancelled/delinked rows. Attribution: allocated → the invoice's sales person; unallocated → the
  sales person of the customer's most recent invoice before the payment date, flagged "attributed by customer".
  *Invoiced*: net of returns, by posting date. *Delivery fees*: charge rows to `delivery_charge_account` by invoice
  driver → `Driver.employee`. *Units*: qty converted to carton UOM. *Tender collections*: Collected measure limited
  to `is_tender` invoices (each partial collection counts in the month received).
- `periods.py` — returns the months a rule needs for a payout period: Monthly = that month; Quarterly Average =
  the three months of the quarter (payable only when the run period is a quarter); Rolling = month + 2 prior.
  Missing months come from Manual Figures.
- `tiers.py` — pure functions: `fixed_step`, `fixed_plus_excess`, `flat_rate`; headcount scaling of thresholds
  (and amounts only when `scale_amounts`). Thresholds inclusive; below the first tier = 0 with tier "None".
- `recipients.py` — resolves people for a period: tree members filtered by designation, supervisor = `employee`
  on the Sales Person group node (standard field), designation/department matches for shares, then applies
  Commission Assignments (Assistant Of, Pool Share %, Include/Exclude). Employee eligible if Active on any day
  of the period; full amount (my call, open question G3).
- `distribution.py` — splits a pool into shares, then within a share Equal or By Assignment %.
  Shares not totalling 100% → status "Needs setup".
- `engine.py` — `calculate(plan, period_start, period_end) -> list[CommissionLine]`; one call per rule, then
  distribution. Also `check_setup(plan, period)` returning plain-language problems
  ("Sales Person Prabhu has no employee", "Group Cash Market Salesman Sales has no supervisor",
  "Hypermarket shares total 95%", "March 2026 manual figure missing").
- Whitelisted API: `get_commission_lines`, `check_setup`; the report and the Run both call the engine.

### 6.3 How each category maps to configuration (seeded as the "Commission Map Jan–Jun 2026" plan)

| Category / role | Basis | Period | Tier method & numbers | Recipients |
|---|---|---|---|---|
| Traditional – Salesperson | Collected, Cash Customers, excl. unit-rate items | 3-mo avg | Fixed Step 70k→200, 84k→367, 105k→1,050, 131.25k→2,362.5, 157.5k→3,937.5 + 3.5% excess | each attributed sales person in cash group, designation Salesman |
| Traditional – Cashier Assistant | Paired (salesman rule) | same | Fixed Step 75/125/200/300/400 + 0.45% on same thresholds | Assignments "Assistant Of" |
| Traditional – Supervisor | sum of team salesmen's basis | 3-mo avg | Fixed Step 672k→1,344, 840k→2,646, 1.05M→4,966.5, 1.26M→7,938 + 1% excess (the full map; 4 tiers); base 8, targets scale | `employee` of each cash sub-group |
| Traditional – Tea Milk | Units of MR-MILK-00014 (Ctn) | Monthly | unit rate 1 QAR | invoice sales person |
| Modern – Salesperson pool | Invoiced, hypermarket groups | 3-mo avg | Fixed + Excess %: 600k→0, 700k→1,800, 900k→1,800+1.25%, 1.1M→2,500+1.75%, >1.1M 3,500+2% (rows editable; reading flagged M1) | Pool → Pool Share % assignments |
| Modern – Supervisor | same | 3-mo avg | 700k→0, 900k→1,000, 1.1M→2,000, >1.1M 2,000+1.5% | `employee` of hypermarket group |
| Sales Mgmt – Manager/Assistant | Company Sales = Cash collected + Hypermarket invoiced | 3-mo avg | 1.5M→0, 1.6M→2,000, >1.6M 2,000+2% | Pool → shares Manager 60 (Sales Head) / Assistant 40 (Sales Manager) |
| Sales Mgmt – Coordinator | same | 3-mo avg | Fixed Step 1.5M→350 | designation Sales Coordinator |
| Smile24 – Online salesperson | Invoiced, Online Sales | Monthly | Fixed Step 20k→200, 30k→720, 50k→1,700, 70k→2,800 + 5% | invoice sales person |
| Smile24 – Drivers | Delivery fees | Monthly | Flat 50% + 5 QAR per free order beyond 100 | invoice driver |
| Logistics – Team | Company Sales: all groups except Online Sales & Direct Sales | Monthly | tiers **empty**, rule flagged waiting; base 8 drivers, targets scale, amounts fixed | Pool → Drivers 60 (Delivery Driver), Workers 40 (labor), Equal |
| Tenders | Tender collections | Monthly | Flat 1.5% | Pool → Sales 40 / Management 60 via Share Member assignments (waiting until set) |

The default plan is created by a whitelisted "Create default plan" action on Commission Settings
(idempotent; never fixtures).

### 6.4 Report: Sales Commission & Incentive

- Filters: Company, Plan (defaults to the plan covering the period), Period Type (Month / Quarter),
  Month or Quarter selector, Category, Employee, View (**Summary by Employee** default / Detail).
- Summary: one row per employee, one column per category, total; footer totals "Payable" and "Not assigned".
- Detail: employee, sales person, category, rule, role/share, basis, period months and values, average,
  target (scaled), tier "2 of 5", next target and gap, fixed part, excess part, share %, amount, status, notes.
- Above the table: setup problems from `check_setup`; banner when an approved run differs.
- Excel export: standard report export (works for both views).
- Roles: new role **Commission Manager** (created by patch) edits plans/rules/assignments and approves runs;
  Sales Manager and Accounts Manager read the report.

### 6.5 Client UX (Desk) — user requirement: configuration must be easy for the client's admin

Decided: Desk only (custom Desk Page + Desk forms/dialogs). No Frappe UI app; `sabaa` has no frontend build.
The user is a non-technical sales/accounts admin. They think in "categories, numbers and people", never in
"basis sources" or "recipient sources". Every screen below follows that.

**1. Commission Setup page** (Desk Page `commission-setup`, the single entry point; workspace shortcut).
- Top: plan selector (defaults to the plan covering today) and month selector. One primary action:
  **Check setup** (it reruns automatically when the page opens).
- Body: one row per rule, grouped by the six categories. Each row shows the rule name, a status chip
  (Ready · Needs setup · Waiting for business), and one line in plain words
  ("5 tiers · 3-month average · 11 salesmen").
- Under a non-Ready row: each problem in one sentence with a **Fix** link that opens the exact place:
  "Prabhu has no employee → Fix" opens the Sales Person; "Hypermarket shares total 95% → Fix" opens the
  People dialog; "March 2026 figures missing → Fix" opens the figures grid.
- Footer actions: "Create default plan" (first use only, when no plan exists), "Copy plan to new period"
  (dialog with the new dates), "Open report".
- Empty state on first use: one sentence plus the "Create default plan" button.

**2. Rule form via templates.**
- "New rule" opens a dialog that lists templates by category ("Traditional Trade – Salesperson", …).
  The template fills basis, sources, attribution, recipient source and shares. The admin names the rule and
  edits numbers and people only.
- Form order: Summary (read-only sentence: "Each cash salesman earns by collected sales, 3-month average")
  · **Tiers** · **People & split** · **Period** · Advanced (collapsed: basis, sources, attribution,
  recipient source, headcount scaling, multiplier). `depends_on` hides fields that do not apply.
- **Tier editor:** each row reads "From 70,000 QAR → 200 QAR (+3.5% above)". Server validation in plain
  words: thresholds must increase; percent 0–100. Under the table, a **Try an amount** field shows the live
  result ("120,000 → Tier 3 of 5 → 1,050 QAR"; with headcount scaling also "target for 9 drivers: 900,000").
- "Waiting for business" checkbox with a note. The report shows the note instead of amounts.

**3. People dialog** (button "People" on the rule and Fix links).
- Lists who will be paid for the selected month, with the source as a small badge: From HR tree ·
  By designation · Added by hand · Excluded.
- Inline actions: add a cashier assistant to a salesman, set share %, exclude or include a person,
  each with an optional from/to date. Live share total ("100% ✓" / "95%, 5% missing").
- Saving writes Commission Assignments; the admin never opens the Assignment list for normal work.

**4. Missing months grid** (dialog from the Setup page).
- Rows = sales persons (or "Company" for company-level rules); columns = the months the plan needs but
  ERPNext does not hold (March, April 2026). Paste from Excel works (tab-separated). Saves Manual Figures.

**5. Commission Run.**
- One primary button per status: Calculate → Approve → Mark Paid. Before Approve: a confirm dialog with
  the total, the number of employees and any "Not assigned" amount.
- A "Changes since approval" box when the live result now differs from the approved lines.

**6. Report.** Month (or Quarter) picker, not two date fields; Summary by Employee is the default view;
status chips use Frappe indicator colours (green Ready, orange Needs setup, grey Waiting); setup problems
appear above the table with the same Fix links.

**UX acceptance checks** (done in the browser before handover):
- From an empty site, an admin can create the default plan and reach "Ready" for one category without
  opening any list view or the Advanced section.
- Every problem message names the person or rule and has a working Fix link.
- Changing a tier and using "Try an amount" gives the same figure as the report.

### 6.6 Testing

- Unit tests (no DB) for `tiers.py`, `periods.py`, `distribution.py`: every tier boundary of every seeded rule,
  excess, headcount scaling (9 drivers → 800k target 900k, amount unchanged), partial tender collections,
  shares not 100%.
- Integration tests (FrappeTestCase) with built invoices/payments: collected attribution incl. unallocated JE,
  Direct Sales exclusion, Tea Milk removed from basis, manual figure months, Commission Run status transitions
  and duplicate-run guard.
- Validation: run May and June 2026 on `sabaa.local` and compare with the booked commission accounts.

## 7. Open business questions (shown as statuses in the report until answered)

G1 Do credit notes/discounts to cash customers reduce collected sales? (default: no)
G2 Do Van Sales and Horeca count in Traditional/Company sales? (default: Logistics yes, others no)
G3 Mid-month joiner/leaver: full, pro-rata or zero? (default: full if active any day)
G4 Three-month average: fixed quarters (Jan–Mar, Apr–Jun) or rolling? Is the tier amount paid once per payout
or per month (×3 for a quarter)? (default: per rule set; multiplier 1)
G5 Do collections that settle the pre-ERPNext opening balance count? (default: yes, attributed by customer)
T1 How is a tender identified? (default: `is_tender` checkbox) · T2 Who receives Sales 40% and Management 60%?
L1 Logistics tier targets and amounts · L2 Workers = Sales labor only, or Inventory labor too? (default: Sales)
S1 Which salesmen belong to each cash supervisor? (needs tree split into sub-groups) · S2 Who are the cashier
assistants and their salesmen? · S3 Supervisor tiers with fewer than 8 salesmen: targets only, or amounts too?
M1 Modern Trade "up to" reading (899k pays more than 900k as written) · M2 The 12 salespersons and their shares
SM1 Is 2,000 earned from 1.5M or 1.6M?
O1 Smile24 salesperson on invoiced or collected sales? · O2 The 2 online salespersons (all invoices show
Mohammed Irfan) · O3 "Free delivery exceeding 100": per order above 100 QAR, or each free order after the 100th?
U1 Per-carton items: do returns deduct? Other items (Memories 2 QAR, Abu Walad 5 QAR)?

## 7a. Calls I made (please check)

- Runs are always monthly; quarterly-average rules pay in the quarter's last month only.
- An approved/paid run locks its plan's rules and the assignments and manual figures dated in that month.
- Tender = `is_tender` checkbox on Sales Invoice.
- Supervisor = `employee` on the Sales Person group node; the cash group is split into one sub-group per supervisor.
- Unallocated collections go to the sales person on the customer's most recent invoice, flagged.
- Employees active on any day of the month get the full amount.
- Logistics workers default to labor in the Sales department.
- Payout multiplier 1, and opening-balance collections count, until the business answers G4/G5.

## 7b. After approval (first steps)

1. `git stash -u` on `feat/sales-commission-report`; `git switch -c feat/sales-commission-v2 develop`.
2. Save this design as `docs/superpowers/specs/sales-commission-report/design.md`; commit
   `docs(commission): add sales commission design`.
3. Invoke `superpowers:writing-plans` to produce the implementation plan.

## 8. Left to the builder

File layout inside `sabaa/commission/`, query shapes, column widths, form layout details, test fixtures data,
naming series, and the exact wording of setup-check messages.

## 9. Verification

1. `bench --site sabaa.local run-tests --app sabaa --module sabaa.commission...` and the DocType/report tests.
2. `bench --site sabaa.local migrate` on the new branch after dropping the old commission tables.
3. Walk the UX acceptance checks in 6.5 in the browser (agent-browser); then create default plan; run Check setup; run the report for May 2026 (Month) and Q2 2026 (Quarter) in both
   views; export to Excel; create, calculate, approve and mark paid a Commission Run; cancel and re-run.
4. Compare May/June figures with booked commission account balances; list differences with causes.
