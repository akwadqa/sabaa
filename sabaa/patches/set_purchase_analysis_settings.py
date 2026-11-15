import frappe

# The first Purchase Analysis Index kept these values in its code.
MAIN_STORE_WAREHOUSE = "Warehouse (Main Store) - STG"
VAN_SALES_WAREHOUSE = "136 - Van Sales Store - STG"
PROMOTIONAL_UOMS = ("Outer", "Set", "Box")
PROMOTIONAL_NAME_MARKER = "G.P"


def execute():
	settings = frappe.get_single("Purchase Analysis Settings")

	if not settings.main_store_warehouse and frappe.db.exists("Warehouse", MAIN_STORE_WAREHOUSE):
		settings.main_store_warehouse = MAIN_STORE_WAREHOUSE
	if not settings.van_sales_warehouse and frappe.db.exists("Warehouse", VAN_SALES_WAREHOUSE):
		settings.van_sales_warehouse = VAN_SALES_WAREHOUSE
	if not settings.promotional_uoms:
		for uom in PROMOTIONAL_UOMS:
			if frappe.db.exists("UOM", uom):
				settings.append("promotional_uoms", {"uom": uom})
	if not settings.promotional_name_markers:
		settings.promotional_name_markers = PROMOTIONAL_NAME_MARKER

	settings.save()
