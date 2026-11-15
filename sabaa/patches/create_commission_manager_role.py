import frappe

from sabaa.sabaa.commission.constants import COMMISSION_MANAGER


def execute():
	if frappe.db.exists("Role", COMMISSION_MANAGER):
		return
	frappe.get_doc({"doctype": "Role", "role_name": COMMISSION_MANAGER, "desk_access": 1}).insert()
