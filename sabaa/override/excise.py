import frappe
from frappe import _
from frappe.utils import flt

EXCISE_ACCOUNT_NAME = "Excise Tax Recoverable"
EXCISE_TAX_DESCRIPTION = "Excise Tax Recoverable"


def calculate_item_excise(doc, method=None):
    """
    Item-wise Excise Tax Recoverable calculation for Sales Invoice.

    Must run on `before_validate` (not `validate`): the standard ERPNext
    Sales Invoice validate() chain already calls calculate_taxes_and_totals()
    once via SellingController.validate() -> super().validate(), before any
    `validate` doc_event hook fires. Registering on `before_validate` ensures
    the Excise "Actual" tax row exists before that first (and only) pass, so
    grand_total/GL reflect it without any custom totals/GL code.
    """
    excise_account = _get_excise_account(doc.company)

    total_excise = 0.0

    for item in doc.get("items") or []:
        item.custom_excise_rate = 0
        item.custom_excise_amount = 0

        if not item.item_code or item.get("is_free_item"):
            continue

        is_excisable, excise_rate = frappe.get_cached_value(
            "Item", item.item_code, ("custom_is_excisable", "custom_excise_rate")
        )

        if not is_excisable:
            continue

        if not excise_rate:
            frappe.throw(
                _(
                    "Item {0} is marked as Excisable but has no Excise Amount configured. "
                    "Please set <b>Excise Amount (per Default UOM)</b> in the Item master."
                ).format(frappe.get_desk_link("Item", item.item_code))
            )

        base_qty = flt(item.qty) * (flt(item.conversion_factor) or 1)
        excise_amount = flt(base_qty * flt(excise_rate), item.precision("amount"))

        item.custom_excise_rate = excise_rate
        item.custom_excise_amount = excise_amount

        total_excise += excise_amount

    total_excise = flt(total_excise, doc.precision("net_total"))
    doc.custom_total_excise = total_excise

    _upsert_excise_tax_row(doc, excise_account, total_excise)


def _get_excise_account(company):
    abbr = frappe.get_cached_value("Company", company, "abbr")
    account = f"{EXCISE_ACCOUNT_NAME} - {abbr}"

    if not frappe.db.exists("Account", account):
        frappe.throw(
            _(
                "Account {0} does not exist for Company {1}. "
                "Please create it before submitting Excisable Sales Invoices."
            ).format(frappe.bold(account), frappe.bold(company))
        )

    return account


def _upsert_excise_tax_row(doc, excise_account, total_excise):
    existing_row = None
    for tax in doc.get("taxes") or []:
        if tax.account_head == excise_account:
            existing_row = tax
            break

    if not total_excise:
        # Exactly zero (e.g. no excisable items on this row set) -> no tax
        # row at all, matching the print template's `{% if tax.tax_amount %}`
        # guard. Negative totals (returns) are posted, not suppressed.
        if existing_row:
            doc.taxes.remove(existing_row)
        return

    if existing_row:
        existing_row.tax_amount = total_excise
        existing_row.charge_type = "Actual"
    else:
        doc.append(
            "taxes",
            {
                "charge_type": "Actual",
                "account_head": excise_account,
                "tax_amount": total_excise,
                "description": EXCISE_TAX_DESCRIPTION,
            },
        )
