# Woqod Invoice Stamp: Design

Analysis page with the saved answers: https://claude.ai/artifact/THp6Va2zxb5UPQDUxuLkQ3

## 1. Requirement

Print the company stamp on the invoices of Woqod Group customers. Do not print it on the invoices of other customers.

## 2. Decisions

The user answered all 11 questions on 19 Nov 2026.

| Q | Decision |
|---|---|
| Q1 | Both groups get the stamp: `Woqod Group` and `Woqod Group (G.W)`. |
| Q2 | A check field "Print Stamp on Invoice" on Customer Group marks the groups. The deploy ticks the two Woqod groups. |
| Q3 | The customer group saved on the invoice (`Sales Invoice.customer_group`) decides. The current group of the customer is not used. |
| Q4 | The print format adds the stamp each time the invoice prints. No file is stored. |
| Q5 | The stamp follows the invoice brand. A `GW` naming series gets the Green World stamp. Other series get the Saba stamp. |
| Q6 | Submitted invoices and submitted returns get the stamp. Drafts and cancelled invoices do not. |
| Q7 | The stamp is in the "Authorized Signature" box. |
| Q8 | Only the print format "Sales Invoice - Custom" shows the stamp. |
| Q9 | A reprint of an old submitted invoice also shows the stamp. |
| Q10 | The two stamp images are fields in a new "Invoice Stamp" section of App Settings. An administrator can replace them. App Settings is in the van_sales app, so a sabaa patch adds the fields as custom fields. van_sales does not change. |
| Q11 | Stamp only. No signature image. |

## 3. Facts from the code and the data

- "Sales Invoice - Custom" is a standard Jinja print format in `sabaa/sabaa/print_format/sales_invoice___custom/`. It is the desk default. The Mobile App uses it too, through App Settings `si_print_format` and `van_sales.van_sales.api.print.get_document_html`.
- The format picks the brand with `doc.naming_series.startswith("GW")`. Saba and Green World are one company, "Saba Trading Group".
- `get_document_html` makes `/files/...` and `/private/files/...` URLs absolute. The Mobile App renders the HTML without a desk session, so a private file does not show.
- App Settings (van_sales, single) has the fields `default_customer_grp`, `default_price_list`, `default_customer_type`, then the section `print_formats_section` with `si_print_format`, `pe_print_format` and `so_print_format`.
- On sabaa.local: `Woqod Group` (119 customers) and `Woqod Group (G.W)` (93 customers). 446 Woqod invoices, 176 of them returns.

## 4. Flow

1. An administrator uploads the Saba stamp and the Green World stamp in App Settings → Invoice Stamp.
2. The deploy patch ticks "Print Stamp on Invoice" on the two Woqod groups.
3. A user prints, emails or downloads an invoice, or the Mobile App asks for its HTML.
4. The print format calls `get_invoice_stamp_url(doc)`.
5. The method returns the stamp URL when all of these are true. Otherwise it returns `None`:
   - `doc.docstatus` is 1.
   - `doc.customer_group` has "Print Stamp on Invoice" ticked.
   - The App Settings image for the brand of the invoice is set.
6. The format shows the image in the "Authorized Signature" box. Without a URL, the box is the same as today.

## 5. Schema

Patch `sabaa.patches.add_invoice_stamp_fields` (`post_model_sync`), with `create_custom_fields(..., ignore_validate=True, update=True)` and `"module": "Sabaa"`:

| DocType | Fieldname | Type | Label | Insert after |
|---|---|---|---|---|
| Customer Group | `custom_print_stamp_on_invoice` | Check | Print Stamp on Invoice | `is_group` |
| App Settings | `custom_invoice_stamp_section` | Section Break | Invoice Stamp | `so_print_format` |
| App Settings | `custom_saba_invoice_stamp` | Attach Image | Saba Stamp | `custom_invoice_stamp_section` |
| App Settings | `custom_green_world_invoice_stamp` | Attach Image | Green World Stamp | `custom_saba_invoice_stamp` |

- Customer Group field description: "Print the company stamp on submitted Sales Invoices of this group."
- Section description: "Upload transparent PNG files as public files. The stamp prints on submitted Sales Invoices of customer groups with Print Stamp on Invoice ticked."

Patch `sabaa.patches.enable_invoice_stamp_for_woqod_groups` (`post_model_sync`, after the field patch): set the check to 1 on `Woqod Group` and `Woqod Group (G.W)`, for each group that exists. It does not stop when a group is missing.

## 6. Code

### 6.1 `sabaa/sabaa/invoice_stamp/__init__.py`

- `GREEN_WORLD_SERIES_PREFIX = "GW"`. This is the same rule as `is_greenworld` in the print format.
- `class InvoiceStampError(frappe.ValidationError)`.
- `class InvoiceStamp`, built with a Sales Invoice document:
  - `is_due` (property): docstatus 1 and the flag is set on `doc.customer_group`. It reads the flag with `frappe.get_cached_value`.
  - `is_green_world` (property): `(doc.naming_series or "").startswith(GREEN_WORLD_SERIES_PREFIX)`.
  - `url` (property): `None` when not due. Otherwise the App Settings image for the brand, or `None` when it is empty.
- `get_invoice_stamp_url(doc) -> str | None`: the Jinja method. It returns `InvoiceStamp(doc).url`.
- `validate_stamp_files(doc, method=None)`: the App Settings `validate` hook. It refuses a stamp URL that starts with `/private/` and raises `InvoiceStampError` with: "Upload {label} as a public file. The Mobile App cannot show private files on invoices."

### 6.2 `sabaa/hooks.py`

- Add `sabaa.sabaa.invoice_stamp.get_invoice_stamp_url` to `jinja["methods"]`.
- Add `"App Settings": {"validate": "sabaa.sabaa.invoice_stamp.validate_stamp_files"}` to `doc_events`.

### 6.3 Print format "Sales Invoice - Custom"

- In the left `sign-box`, put the image in `sign-space`: `<img src="{{ stamp_url }}" class="sign-stamp" alt="Company stamp">`, only when `stamp_url` is set.
- CSS: `.sign-space { position: relative; }` and `.sign-stamp { position: absolute; left: 50%; bottom: -12px; transform: translateX(-50%); max-width: 100px; max-height: 100px; }`. The image does not change the layout of an invoice without a stamp.
- Update `modified` in the JSON, so `migrate` loads the new version.

## 7. Out of scope

- Other Sales Invoice print formats, Delivery Notes, Sales Orders and Payment Entries.
- A stored stamped PDF.
- A signature image.
- Changes in van_sales or in the Mobile App.

## 8. Risks

- The print format on staging or production can differ from the repo version. Compare the site version with the repo version before the deploy (Phase 3).
- The stamp images do not exist yet. The client sends them as transparent PNG files. Without an image, invoices print as today.
- A stamp that is too large can cover the company name in the box. Check the size on a real PDF (Phase 2 and Phase 3).
