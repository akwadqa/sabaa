# Invoice Stamp: User Guide

The system prints the company stamp in the "Authorized Signature" box of a Sales Invoice. It prints the stamp only for customer groups that have "Print Stamp on Invoice" ticked. The stamp shows in desk print, PDF, email and the Mobile App.

## Upload the stamps

Do this one time, and again when a stamp changes.

1. Open **App Settings**.
2. Go to the **Invoice Stamp** section.
3. In **Saba Stamp**, attach the Saba stamp.
4. In **Green World Stamp**, attach the Green World stamp.
5. Click **Save**.

Use a PNG file with a transparent background, so the text under the stamp stays readable. In the upload dialog, clear **Is Private** before you click **Upload**. The system does not save App Settings with a private stamp file, because the Mobile App cannot show private files.

## Choose the customer groups

1. Open the **Customer Group**.
2. Tick **Print Stamp on Invoice** to print the stamp. Clear it to stop.
3. Click **Save**.

The update set this tick on "Woqod Group" and "Woqod Group (G.W)".

## Which invoices get the stamp

An invoice gets the stamp when all these conditions are true:

- The invoice is submitted. Returns (credit notes) are included. Drafts and cancelled invoices do not get the stamp.
- The customer group on the invoice has "Print Stamp on Invoice" ticked. The system uses the group saved on the invoice, not the customer's group today.

The naming series of the invoice selects the stamp:

| Naming series | Stamp |
|---|---|
| Starts with `GW`, for example `GW/SIV/00228/2026` | Green World Stamp |
| Any other series, for example `SIV/22622/2026` | Saba Stamp |

Example: invoice `GW/SIV/00233/2026` for a customer in "Woqod Group" prints the Green World stamp.

## When a stamp is missing

If the stamp field for the invoice brand is empty, the invoice prints without a stamp. There is no error. The signature box stays the same as before.

A change to a stamp or to the tick shows the next time someone prints the invoice. Invoices that were already printed or sent do not change.
