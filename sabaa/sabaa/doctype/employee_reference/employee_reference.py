# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


def _pending_own_attachment_cache_key(reference_name):
	return f"employee_reference_pending_own_attachment:{reference_name}"


class EmployeeReference(Document):
	def before_save(self):
		if self.is_new() or not self.is_current:
			return

		before = self.get_doc_before_save()
		if not before:
			return

		if not self.has_value_changed("attachment"):
			return

		cache_key = _pending_own_attachment_cache_key(self.name)

		if not self.attachment:
			if before.attachment:
				frappe.cache().set_value(cache_key, before.attachment, expires_in_sec=3600)
			return

		stashed = frappe.cache().get_value(cache_key)
		previous = stashed or before.attachment
		frappe.cache().delete_value(cache_key)

		if previous:
			self.previous_attachment = previous

	def on_trash(self):
		if frappe.db.exists("Employee Reference", {"previous_reference": self.name}):
			frappe.throw(
				_("Cannot delete {0}: a newer renewal reference links back to it as its previous reference.").format(
					self.name
				)
			)

	@frappe.whitelist()
	def make_renewal(self):
		new_reference = frappe.new_doc("Employee Reference")
		new_reference.employee = self.employee
		new_reference.document = self.document
		new_reference.designation = self.designation
		new_reference.license_type = self.license_type
		new_reference.old_document_no = self.reference_no
		new_reference.previous_attachment = self.attachment
		new_reference.previous_reference = self.name
		new_reference.insert()

		self.is_current = 0
		self.save()

		return new_reference.name


@frappe.whitelist()
def renew_reference(reference):
	doc = frappe.get_doc("Employee Reference", reference)
	doc.check_permission("write")
	return doc.make_renewal()
