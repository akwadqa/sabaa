# Sales Commission Report – Phase 3: Sources

> Read `plan-overview.md` first: it holds the global constraints, review focus and file map that apply to every task here.

### Task 6: Sales sources — collected and invoiced

**Files:** Create `sabaa/sabaa/commission/sources.py`, `sabaa/sabaa/commission/tests/test_sources.py`, `sabaa/sabaa/commission/tests/factories.py` (shared builders: customer in group, sales person with employee, invoice with sales team, payment entry, journal entry).

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class BasisRow: month: date; key: str | None; amount: float; flag: str | None = None` — `key` is the sales person (or driver employee) the amount belongs to; `None` = unattributed.
  - `expand_customer_groups(groups: list[str], excluded: list[str]) -> list[str]` (descendants via lft/rgt, minus excluded and their descendants).
  - `get_invoiced(company, customer_groups, from_date, to_date, exclude_items: list[str] = ()) -> list[BasisRow]` — `base_net_total` of submitted invoices incl. returns (negative), per posting month and invoice sales person; `exclude_items` subtracts those items' `base_net_amount`.
  - `get_collected(company, customer_groups, from_date, to_date, exclude_items: list[str] = ()) -> list[BasisRow]` — per payment month:
    - Payment Ledger Entry rows, `party_type` Customer, `delinked` 0, `amount < 0`, `voucher_type` in (Payment Entry, Journal Entry), whose voucher has a GL row on an account in `Company.sales_collection_accounts`; exclude `is_opening` vouchers.
    - POS `paid_amount − change_amount` of `is_pos` invoices, by posting month.
    - Attribution: `against_voucher` is a Sales Invoice → its sales person; against the opening entry → if `count_opening_balance_collections`, the customer's latest invoice sales person with flag `"opening balance"`, else skipped; unallocated → the customer's latest invoice before the payment date with flag `"attributed by customer"`; no invoice at all → `key=None`, flag `"no sales person"`.
    - `exclude_items` subtracts those items' invoiced net amount for invoices posted in the same month by the same sales person.
- Excluded groups always include the plan's `excluded_customer_groups` (callers pass them).

- [ ] **Step 1: Failing integration tests** (FrappeTestCase, savepoint per test, factories):
  - `test_invoiced_nets_returns` — 10,000 invoice + 2,500 return in May → one row 7,500.
  - `test_direct_sales_excluded` — invoice in `Direct Sales` group absent.
  - `test_collected_allocated_payment` — invoice 4/2026-05-03 by "SP A", payment entry 2026-06-02 to a collection account → row (June, "SP A", amount).
  - `test_credit_note_journal_not_collected` — JE crediting the customer against a non-collection account → no row.
  - `test_unallocated_journal_attributed_by_customer` — flag `"attributed by customer"`.
  - `test_pos_paid_amount_counted`.
  - `test_unit_items_removed_from_collected_basis` — 1,000 sale with 200 of Tea Milk, collected 1,000 → 800.
  - `test_negative_month_allowed` — return larger than sales → negative row, no error (Review Focus 2).
- [ ] **Step 2–4:** FAIL → implement → PASS
- [ ] **Step 5: Commit** — `feat(commission): read collected and invoiced sales`

---

### Task 7: Other sources — delivery fees, units, tender collections

**Files:** Modify `sabaa/sabaa/commission/sources.py`; test `sabaa/sabaa/commission/tests/test_sources_other.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class DeliveryRow: month: date; driver: str | None; employee: str | None; fee_amount: float; free_order_count: int`
  - `get_delivery_fees(company, customer_groups, from_date, to_date, account: str) -> list[DeliveryRow]` — fee = invoice item rows (and tax rows) booked to `account`; free order = invoice with no such row; grouped by month and `Sales Invoice.driver` → `Driver.employee`.
  - `get_units(company, customer_groups, from_date, to_date, unit_rates: list[frappe._dict], carton_uom: str) -> list[BasisRow]` — `amount` = cartons × `amount_per_unit`, cartons = `stock_qty / conversion_factor(item, carton_uom)`, returns negative (U1 default), attributed to the invoice sales person.
  - `get_tender_collections(company, from_date, to_date) -> list[BasisRow]` — `get_collected` limited to allocations against invoices with `is_tender = 1`; `key=None` (pool).

- [ ] **Step 1: Failing tests:** two Smile24 invoices with 15 QAR delivery and one without, same driver → `fee_amount == 30`, `free_order_count == 1`; Driver without employee → `employee is None`; 96 Pcs of Tea Milk at 48/Ctn with rate 1 → amount 2; tender invoice 100,000 with 50,000 collected in June → June row 50,000, nothing in May.
- [ ] **Step 2–4:** FAIL → implement → PASS
- [ ] **Step 5: Commit** — `feat(commission): read delivery fees, units and tender collections`
