import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    try:
        custom_fields = {
            "Employee": [
                {
                    "fieldname": "official_papers_tab",
                    "label": _("Official Papers"),
                    "fieldtype": "Tab Break",
                    "insert_after": "place_of_issue",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "official_papers_section_1",
                    "fieldtype": "Section Break",
                    "insert_after": "official_papers_tab",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "custom_employee_qid",
                    "label": _("Employee QID"),
                    "fieldtype": "Data",
                    "insert_after": "official_papers_section_1",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "qid_expiry",
                    "label": _("QID Expiry"),
                    "fieldtype": "Date",
                    "insert_after": "custom_employee_qid",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "passport_file",
                    "label": _("Passport File"),
                    "fieldtype": "Attach",
                    "insert_after": "qid_expiry",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "nationality",
                    "label": _("Nationality"),
                    "fieldtype": "Link",
                    "options": "Nationality",
                    "insert_after": "passport_file",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "nationality_ar",
                    "label": _("Nationality (AR)"),
                    "fieldtype": "Data",
                    "fetch_from":"nationality.nationality_ar",
                    "fetch_if_empty":1,
                    "read_only":1,
                    "insert_after": "nationality",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "column_1_official_papers",
                    "fieldtype": "Column Break",
                    "insert_after": "nationality_ar",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "sponsorship",
                    "label": _("Sponsorship"),
                    "fieldtype": "Link",
                    "options": "Place of Work and Sponsorship",
                    "insert_after": "column_1_official_papers",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "sponsorship_ar",
                    "label": _("Sponsorship (AR)"),
                    "fieldtype": "Data",
                    "fetch_from":"sponsorship.sponsorship_ar",
                    "fetch_if_empty":1,
                    "read_only":1,
                    "insert_after": "sponsorship",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "place_of_work",
                    "label": _("Place of Work"),
                    "fieldtype": "Link",
                    "options": "Place of Work and Sponsorship",
                    "insert_after": "sponsorship_ar",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "place_of_work_ar",
                    "label": _("Place of Work (AR)"),
                    "fieldtype": "Data",
                    "fetch_from":"place_of_work.sponsorship_ar",
                    "fetch_if_empty":1,
                    "read_only":1,
                    "insert_after": "place_of_work",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "job_offer_letter",
                    "label": _("Job Offer Letter"),
                    "fieldtype": "Attach",
                    "insert_after": "place_of_work_ar",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "official_papers_section_2",
                    "label": _("Health Insurance"),
                    "fieldtype": "Section Break",
                    "insert_after": "job_offer_letter",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "health_insurance_expiry",
                    "label": _("Health Insurance Expiry"),
                    "fieldtype": "Date",
                    "insert_after": "official_papers_section_2",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "health_insurance_file",
                    "label": _("Health Insurance File"),
                    "fieldtype": "Attach",
                    "insert_after": "health_insurance_expiry",
                    "module": "Sabaa"
                },
            ],
        }

        create_custom_fields(custom_fields, ignore_validate=True, update=True)
    

    except Exception:
        frappe.log_error("Patch Error: Add Custom Fields", frappe.get_traceback())
        raise