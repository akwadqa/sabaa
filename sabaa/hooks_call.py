import frappe
from frappe.utils import today
from hrms.hr.doctype.leave_application.leave_application import get_leave_details

def fetch_leave_balance(employee_doc_name): 
    try:
        # Logic identical to Leave Balance Summary Report 
        # leave_types = frappe.db.sql_list("select name from `tabLeave Type` order by name asc")
        leave_types = frappe.db.get_all("Leave Type", pluck="name", order_by="name asc")
        available_leave = get_leave_details(employee_doc_name, today())

        data = []

        for leave in leave_types:
            remaining = 0
            if available_leave.get("leave_allocation", {}) != {}:
                if leave in available_leave["leave_allocation"]:
        		    # opening balance
        	        remaining = available_leave["leave_allocation"][leave].get("remaining_leaves", 0)

            data.append({
                "leave_type": leave,
                "balance": remaining
            })

        return data

    except Exception as e:
        frappe.log_error("Unable to fetch Leave Balance Data", frappe.get_traceback())
        return []