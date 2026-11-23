import frappe

WOQOD_GROUPS = ("Woqod Group", "Woqod Group (G.W)")


def execute():
	for name in WOQOD_GROUPS:
		if frappe.db.exists("Customer Group", name):
			frappe.db.set_value("Customer Group", name, "custom_print_stamp_on_invoice", 1)
