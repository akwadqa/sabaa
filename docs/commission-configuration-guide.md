# Sales Commission: Admin Guide

This guide is for the person who sets up and runs the monthly sales commission in ERPNext.

You need the role **Commission Manager**.

## Where to start

Open **Commission Setup**. Find it in the **Reports** workspace, or type "Commission Setup" in the search bar.

The page shows one row for each commission rule, grouped by category. Each row has a status:

| Status | Meaning |
|---|---|
| Ready | The rule has everything it needs. |
| Needs setup | Something is missing. The problem is shown under the row with a **Fix** link. |
| Waiting for business input | The business has not decided a rule yet. The report shows this status instead of an amount. |

## First setup

1. Open **Commission Settings** and set these fields:
   - **Company**
   - **ERPNext Start Date**: the first month that has invoices in ERPNext (1 May 2026).
   - **Delivery Charge Account**: `4203 - Delivery Charges - STG`.
2. On the **Company** form, make sure **Sales Collection Accounts** lists every cash, bank and cheque account that receives customer payments.
3. Open **Commission Setup** and click **Create default plan**. This makes the plan "Commission Map Jan–Jun 2026" with 12 rules.
4. Click each **Fix** link and correct the problem. Common problems:
   - "Sales Person X has no employee": open the Sales Person and set the Employee.
   - "Driver X has no employee": open the Driver and set the Employee.
   - "Group X has no supervisor": open the Sales Person group and set its Employee to the supervisor. If one group has two supervisors, make one sub-group for each supervisor and move each salesman under the correct sub-group.
   - "April 2026 figure missing": click **Missing months** and enter the March and April totals.
5. When the setup is correct, set the plan's **Status** to **Active**.

## Enter months that are not in ERPNext

The three-month averages for May and June need the March and April totals.

1. On **Commission Setup**, click **Missing months**.
2. Type a total for each person and month. You can also copy rows from Excel and paste them into the box under the table. Each row must have the name first, then one column for each month.
3. Click **Save**.

## Change who is paid

On a rule, click **People**. The dialog shows each person and why they are included:

- **From HR tree**: the person is under the rule's Sales Person group.
- **By designation**: the person has the designation of a share.
- **Added by hand**: someone added the person in this dialog.

In this dialog you can:

- Tick **Exclude** to stop paying a person from the selected month.
- Enter **Share %** for a pool that is split by percentage. The total must be 100% before you can save.
- Use **Add assistant** to pair a cashier assistant with a salesman.

Each change starts on the first day of the selected month. Earlier months do not change.

## Change a rule's numbers

1. Open the rule. The **Tiers** tab shows each tier as a sentence, for example "From 70,000 QAR → 200 QAR".
2. Change the tier rows.
3. Use **Try an amount** to check the result, for example "120,000 → Tier 3 of 5 → 1,050 QAR".

You cannot change the rules of a plan that has an approved run. Copy the plan instead (see "Start a new period").

## Monthly routine

1. Open **Commission Setup**, select the month and click **Check setup**. Fix the problems.
2. Open the report **Sales Commission & Incentive**. Select the month.
   - **Summary by Employee** shows one row for each employee and a **Not assigned** row.
   - **Detail** shows how each amount was calculated: the months, the average, the tier and the share.
   - To export, use **Menu → Export**.
3. Create a **Commission Run** for the plan and month. Click **Calculate**.
4. Check the totals. Click **Approve**. You cannot approve while a line has the status "Needs setup" or "Missing data".
5. After accounts posts the payment, click **Mark Paid** and enter the Journal Entry.

An approved run keeps its figures. If the source documents change later, the run shows "Changes since approval".

Rules with a quarterly average pay only in the run for the last month of the quarter (March, June, September and December).

## Start a new period

On **Commission Setup**, click **Copy plan to new period**. Enter a name and the new dates. The copy is a Draft. Change its rules, then set it to Active.

## Answer an open business question

| Code | Question | Where to change it |
|---|---|---|
| G1 | Do refunds and credit notes reduce collected sales? | Code change. Now they do not. |
| G3 | Is a joiner or leaver paid in full? | Code change. Now an employee active on any day of the month is paid in full. |
| G4 | Quarterly or rolling average? Is the amount paid once or three times? | Rule: **Period** and **Payout Multiplier** (in Advanced). |
| G5 | Do payments of old (pre-ERPNext) balances count? | Commission Settings: **Count Opening Balance Collections**. |
| T1, T2 | Which invoices are tenders, and who gets each share? | Tick **Tender Sale** on the invoice. Set the people with **People** on the Tenders rule, then clear **Waiting for business input**. |
| L1, L2 | Logistics tiers, and which labor are workers | Logistics rule: **Tiers** tab, and the department of the Workers share. |
| S1 | Salesmen of each supervisor | Sales Person tree: one sub-group for each supervisor. |
| S2 | Cashier assistants | Cashier Assistant rule: **People → Add assistant**. |
| S3, M1, SM1 | How to read the tier tables | Rule: **Tiers** tab. |
| M2 | Hypermarket salespersons and their shares | Modern Trade pool rule: **People → Share %**. |
| O1 | Online salesperson on invoiced or collected sales | Rule: **Basis** (in Advanced). |
| O3 | What is a free delivery after 100? | Smile24 Drivers rule: **Bonus After Count**. |
| U1 | Per-carton items and returns | Tea Milk rule: **Unit Rates**. |
