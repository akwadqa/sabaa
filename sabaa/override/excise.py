import frappe
from frappe import _
from frappe.utils import flt

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

    _upsert_excise_tax_row(doc, total_excise)


def _get_excise_account(company):
    account = frappe.get_cached_value("Company", company, "custom_excise_tax_recoverable_account")

    if not account:
        frappe.throw(
            _(
                "Please configure the <b>Excise Tax Recoverable Account</b> on Company {0} "
                "before submitting Sales Invoices for Excisable Items."
            ).format(frappe.bold(company)),
            title=_("Excise Account Not Configured"),
        )

    account_details = frappe.db.get_value(
        "Account", account, ("company", "is_group", "root_type"), as_dict=True
    )

    if not account_details:
        frappe.throw(
            _(
                "The Excise Tax Recoverable Account {0} configured on Company {1} does not exist. "
                "Please reconfigure it on the Company."
            ).format(frappe.bold(account), frappe.bold(company))
        )

    if account_details.company != company:
        frappe.throw(
            _(
                "The Excise Tax Recoverable Account {0} configured on Company {1} belongs to a "
                "different Company ({2}). Please configure an Account that belongs to {1}."
            ).format(frappe.bold(account), frappe.bold(company), frappe.bold(account_details.company))
        )

    if account_details.is_group:
        frappe.throw(
            _(
                "The Excise Tax Recoverable Account {0} configured on Company {1} is a group "
                "Account and cannot be used for postings. Please configure a non-group Account."
            ).format(frappe.bold(account), frappe.bold(company))
        )

    if account_details.root_type != "Asset":
        frappe.throw(
            _(
                "The Excise Tax Recoverable Account {0} configured on Company {1} must be an "
                "Asset Account (found {2})."
            ).format(frappe.bold(account), frappe.bold(company), frappe.bold(account_details.root_type))
        )

    return account


def _upsert_excise_tax_row(doc, total_excise):
    existing_row = None
    for tax in doc.get("taxes") or []:
        if tax.description == EXCISE_TAX_DESCRIPTION:
            existing_row = tax
            break

    if not total_excise:
        if existing_row:
            doc.taxes.remove(existing_row)
        return

    excise_account = _get_excise_account(doc.company)

    if existing_row:
        existing_row.account_head = excise_account
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
