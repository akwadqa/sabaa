# Customer Group Ledger Summary Implementation Plan

Steps use checkboxes (`- [ ]`). Tick each step when it is done.

**Goal:** Add a Script Report in the sabaa app that shows the Customer Ledger Summary figures per Customer Group: Opening, Total Sales, Total Paid, Total Return, Adjustments and Closing.

**Architecture:** The report runs the ERPNext Customer Ledger Summary (`execute`) with the same filters. It adds each customer row to the row of the customer's group and to the rows of all groups above it. The rows follow the Customer Group tree. No existing report or DocType changes.

**Tech Stack:** Frappe 15 / ERPNext 15 Script Report (Python + JS), `FrappeTestCase`.

**Pull request:** [akwadqa/sabaa#10](https://github.com/akwadqa/sabaa/pull/10)

## Decisions

The design was agreed in chat on 2026-11-18.

- **Customer Group tree.** Each row holds its own customers plus all groups below it. Each row has `indent` and `parent_customer_group`. The JS sets `tree: true` and `initial_depth: 1`, so the top groups open and their sub-groups (for example Saba Customers and Green World Customers) start collapsed.
- **Root group.** "All Customer Groups" is never a row and never a parent. Customers directly on the root get their own top-level row.
- **Customer without a group.** The report shows these customers in one top-level row with an empty group, at the end of the list.
- **Groups without activity.** The report shows only groups that have customer rows in the native report.
- **Current group.** Customers are grouped by their current Customer Group, not the group on the invoice.
- **Adjustments.** The native report takes write-offs and discounts out of Paid and shows them in one `adj_<account>` column per account. This report adds those columns into one **Adjustments** column, so Opening + Sales − Paid − Return − Adjustments = Closing.
- **Summary cards.** Total Sales, Total Paid, Total Return and Closing Balance, summed from the top-level rows. `add_total_row` is 0 because the cards give the totals.
- **Values.** The top-level rows add up to the native Customer Ledger Summary totals for the same filters.

### Revision history

- 2026-11-18, first version: a **Group Level** filter (`Level 1`, `Level 2`, `Customer Group`) chose one level of the tree, with a total row.
- 2026-11-18, user feedback: users found Level 1 / Level 2 unclear. The tree view and the summary cards replaced the Group Level filter and the total row.
- After the first review: the first version dropped the `adj_<account>` columns, so Closing did not reconcile. The Adjustments column was added.

## Global Constraints

- App `sabaa`, module `Sabaa`, folder `sabaa/sabaa/report/customer_group_ledger_summary/`.
- Branch `feat/customer-group-ledger-summary` from `develop`, checked out in `apps/sabaa`.
- Report name `Customer Group Ledger Summary`, `ref_doctype` `Sales Invoice`, `add_total_row` 0. Roles: Accounts User, Accounts Manager, Sales Manager, System Manager.
- Columns, in this order:
  - `customer_group` (Link, Customer Group). The link opens in a new tab (CLAUDE.md 11.3).
  - `customer_count` (Int), labelled "Customers".
  - `opening_balance`, `invoiced_amount` ("Total Sales"), `paid_amount` ("Total Paid"), `return_amount` ("Total Return"), `adjustment_amount` ("Adjustments"), `closing_balance`. All Currency with `options: currency`.
  - `currency` (Link, hidden).
- Filters: `company` (reqd, user default), `from_date` (reqd, today minus 1 month), `to_date` (reqd, today), `customer_group` (Link, includes the groups under it), `territory` (Link), `sales_person` (Link). Other native filters are not in scope.
- No fixtures, no `frappe.db.commit()`, no permission bypass. Ruff config in `pyproject.toml`.
- Tests run from `/home/work/saba-bench`: `bench --site sabaa.local run-tests --module sabaa.sabaa.report.customer_group_ledger_summary.test_customer_group_ledger_summary`.

## File Structure

| File | Responsibility |
|---|---|
| `customer_group_ledger_summary.json` | Report record: type, roles, settings |
| `customer_group_ledger_summary.py` | `execute`, `CustomerGroupLedgerSummary`: roll-up, tree rows, columns, summary cards |
| `customer_group_ledger_summary.js` | Filters, tree settings, new-tab link formatter |
| `test_customer_group_ledger_summary.py` | Tests |

## Review Focus

1. A customer directly on a group node (for example the customers directly on "Saba Customers"): the customer is counted in that node's row, so the row is more than the sum of its children. Test: `test_customer_on_group_node_counts_in_its_own_row`.
2. A leaf group directly under the root (for example Cash Customers) is a top-level row. Test: `test_leaf_under_root_is_top_level_row`.
3. The top-level rows and the cards equal the native totals (no double count of child groups, returns or payments). Tests: `test_top_level_rows_sum_to_native_totals`, `test_cards_match_native_totals`.
4. Closing reconciles with the Adjustments column. Test: `test_adjustments_reconcile_closing`.
5. No GL activity in the period: an empty result with no error. Test: `test_no_data_returns_empty`.

---

### Task 1: Report, roll-up logic and tests

**Interfaces:**
- Consumes: `erpnext.accounts.report.customer_ledger_summary.customer_ledger_summary.execute(filters) -> (columns, rows)`. Each row has `party`, `customer_group`, `opening_balance`, `invoiced_amount`, `paid_amount`, `return_amount`, `closing_balance`, `currency` and the `adj_<account>` fields. Adjustment columns have `is_adjustment: 1`.
- Produces:
  - `execute(filters: dict | None) -> (columns, data, None, None, summary)`
  - `class CustomerGroupLedgerSummary` with `run()`, `get_row_groups(group)`, `get_tree_rows(group_totals)`, `get_summary(data)`, `get_columns()`.

- [x] **Step 1: Write the tests.** Test tree: `_Test CGLS Top` (group, under root) > `_Test CGLS Mid` (group) > `_Test CGLS Leaf A`, `_Test CGLS Leaf B`, `_Test CGLS Empty`. Also `_Test CGLS Solo` (leaf, under root).
  Customers: A1 in Leaf A, B1 in Leaf B, M1 directly on Mid, S1 in Solo.
  Data: an invoice of 1,000 for A1, a payment of 400 for A1, a return of 100 for A1, and an invoice of 500 for B1, M1 and S1.
  - `test_tree_rows_roll_up_children`: Top and Mid have `invoiced_amount` 2,000. Mid has `paid_amount` 400, `return_amount` 100, `closing_balance` 1,500 and `customer_count` 3. Leaf A has 1,000 and Leaf B has 500.
  - `test_tree_rows_have_indent_and_parent`: Top (0, None), Mid (1, Top), Leaf A (2, Mid).
  - `test_parent_listed_before_children`: the order is Top, Mid, Leaf A, Leaf B.
  - `test_groups_without_activity_are_hidden`: no row for `_Test CGLS Empty`.
  - `test_customer_on_group_node_counts_in_its_own_row` and `test_leaf_under_root_is_top_level_row` (Review Focus 1–2).
  - `test_cards_match_native_totals` and `test_top_level_rows_sum_to_native_totals` (Review Focus 3).
  - `test_no_data_returns_empty`: a period with no GL entries returns `[]` and cards of 0.
  - `test_customer_without_group_is_listed_last`: the row with an empty group is the last row, with indent 0.
  - `test_adjustments_reconcile_closing`: with a mocked native result, a write-off of 50 goes into `adjustment_amount` and Closing reconciles.
- [x] **Step 2: Create the report JSON** with the values from Global Constraints.
- [x] **Step 3: Write `CustomerGroupLedgerSummary`.**
  - `run`: call the native `execute`. For each customer row, add the amounts to the row of each group from `get_row_groups`, and add the `adj_<account>` fields into `adjustment_amount`.
  - `get_row_groups`: the customer's group and its ancestors, without the root group (unless the customer is on the root).
  - `get_tree_rows`: put each group under its parent, set `indent` and `parent_customer_group`, and sort the groups by name. The empty group is last.
  - `get_summary`: the four cards from the top-level rows.
- [x] **Step 4: Run the tests.** Result on 2026-11-25: 11 tests, OK.
- [x] **Step 5: Commit.** `feat(report): add Customer Group Ledger Summary report` (7cb022d).

### Task 2: Filters UI (JS)

- [x] **Step 1: Add `frappe.query_reports["Customer Group Ledger Summary"]`** with the filters from Global Constraints, the tree settings, and a `formatter` that opens the `customer_group` link with `target="_blank"`.
- [ ] **Step 2: Check in the browser.**
  1. Run `bench --site sabaa.local migrate`.
  2. Open `/app/query-report/Customer Group Ledger Summary`.
  3. Make sure that the top groups show and that Saba Customers and Green World Customers start collapsed.
  4. Make sure that the cards equal the native Customer Ledger Summary totals for the same dates.
  5. Make sure that a Customer Group link opens in a new tab.

### Task 3: Review and handover

- [ ] Run `frappe-code-review` on the branch diff and fix the findings.
- [x] Open the pull request to `develop`: [#10](https://github.com/akwadqa/sabaa/pull/10).
- [ ] Add the report link to the Selling or Accounting workspace only if the user asks. Not in scope by default.
- [ ] Deploy to staging when the user asks.
