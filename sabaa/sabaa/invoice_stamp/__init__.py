import frappe
from frappe import _

# Same brand rule as `is_greenworld` in the "Sales Invoice - Custom" print format.
GREEN_WORLD_SERIES_PREFIX = "GW"

SETTINGS = "App Settings"
STAMP_FIELDS = ("custom_saba_invoice_stamp", "custom_green_world_invoice_stamp")


class InvoiceStampError(frappe.ValidationError):
	pass


class InvoiceStamp:
	"""Decide which stamp, if any, prints on a Sales Invoice."""

	def __init__(self, doc):
		self.doc = doc

	@property
	def is_due(self) -> bool:
		return (
			self.doc.docstatus == 1
			and bool(self.doc.customer_group)
			and bool(
				frappe.get_cached_value(
					"Customer Group", self.doc.customer_group, "custom_print_stamp_on_invoice"
				)
			)
		)

	@property
	def is_green_world(self) -> bool:
		return (self.doc.naming_series or "").startswith(GREEN_WORLD_SERIES_PREFIX)

	@property
	def url(self) -> str | None:
		if not self.is_due:
			return None

		fieldname = "custom_green_world_invoice_stamp" if self.is_green_world else "custom_saba_invoice_stamp"
		return frappe.db.get_single_value(SETTINGS, fieldname) or None


def get_invoice_stamp_url(doc) -> str | None:
	"""Jinja method for print formats: the stamp image URL of a Sales Invoice, or None."""
	return InvoiceStamp(doc).url


def validate_stamp_files(doc, method=None):
	"""App Settings `validate` hook. The Mobile App cannot load private files."""
	for fieldname in STAMP_FIELDS:
		if (doc.get(fieldname) or "").startswith("/private/"):
			frappe.throw(
				_(
					"Upload {0} as a public file. The Mobile App cannot show private files on invoices."
				).format(_(doc.meta.get_label(fieldname))),
				exc=InvoiceStampError,
			)
