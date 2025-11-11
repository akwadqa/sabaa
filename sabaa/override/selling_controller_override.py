import frappe
from frappe import _
from frappe.utils import flt

def custom_validate_selling_price(self):
    try:
        if self.get("is_return") or not frappe.db.get_single_value("Selling Settings", "validate_selling_price"):
            return

        valuation_rate_map = {}
        under_cost_flag = False

        for item in self.items:
            if not item.item_code or item.is_free_item:
                continue

            last_purchase_rate, is_stock_item = frappe.get_cached_value(
                "Item", item.item_code, ("last_purchase_rate", "is_stock_item")
            )

            last_purchase_rate_in_sales_uom = last_purchase_rate * (item.conversion_factor or 1)

            if flt(item.base_net_rate) < flt(last_purchase_rate_in_sales_uom):
                under_cost_flag = True

            if not is_stock_item:
                continue

            valuation_rate_map[(item.item_code, item.warehouse)] = None

        if valuation_rate_map:
            or_conditions = (
                f"""(item_code = {frappe.db.escape(v[0])}
                and warehouse = {frappe.db.escape(v[1])})"""
                for v in valuation_rate_map
            )

            valuation_rates = frappe.db.sql(
                f"""
                select item_code, warehouse, valuation_rate
                from `tabBin`
                where ({" or ".join(or_conditions)}) and valuation_rate > 0
                """,
                as_dict=True,
            )

            for rate in valuation_rates:
                valuation_rate_map[(rate.item_code, rate.warehouse)] = rate.valuation_rate

            for item in self.items:
                if not item.item_code or item.is_free_item:
                    continue

                last_valuation_rate = valuation_rate_map.get((item.item_code, item.warehouse))
                if not last_valuation_rate:
                    continue

                last_valuation_rate_in_sales_uom = last_valuation_rate * (item.conversion_factor or 1)

                if flt(item.base_net_rate) < flt(last_valuation_rate_in_sales_uom):
                    under_cost_flag = True

        if under_cost_flag:

            try:
                if frappe.db.exists("Workflow", "Selling Under Cost"):
                    is_active = frappe.db.get_value("Workflow", "Selling Under Cost", "is_active")
                    if not is_active:
                        frappe.db.set_value("Workflow", "Selling Under Cost", "is_active", 1)
                        frappe.msgprint(_("Workflow 'Selling Under Cost' has been activated automatically."))
                    else:
                        frappe.logger().info("Workflow 'Selling Under Cost' was already active.")
                else:
                    frappe.msgprint(_("Workflow 'Selling Under Cost' not found."))
                    frappe.log_error("Workflow 'Selling Under Cost' not found.", "Under Cost Workflow Activation")
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), "Error activating 'Selling Under Cost' workflow")
                frappe.throw(_("An error occurred while activating 'Selling Under Cost' workflow. Check Error Logs."))
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in custom_validate_selling_price")
        frappe.throw(_("Unexpected error during selling price validation. Please check Error Logs."))
