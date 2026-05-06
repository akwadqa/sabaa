import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe import _

def execute():
    try:
        custom_fields = {
            "Employee": [
                {
                    "fieldname": "insured",
                    "label": _("Insured"),
                    "fieldtype": "Check",
                    "insert_after": "official_papers_section_3",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "health_certificate_issue_date",
                    "label": _("Health Certificate Issue Date"),
                    "fieldtype": "Date",
                    "insert_after": "insured",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "column_3_official_papers",
                    "fieldtype": "Column Break",
                    "insert_after": "health_certificate_issue_date",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "health_insurance_expiry",
                    "label": _("Health Certificate Expiry Date"),
                    "fieldtype": "Date",
                    "insert_after": "column_3_official_papers",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "official_papers_section_4",
                    "label": _("Driving Information"),
                    "fieldtype": "Section Break",
                    "insert_after": "health_insurance_file",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "driver_id",
                    "label": _("Driver ID"),
                    "fieldtype": "Link",
                    "options": "Driver",
                    "insert_after": "official_papers_section_4",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "driving_license",
                    "label": _("Driving License"),
                    "fieldtype": "Data",
                    "fetch_from":"driver_id.license_number",
                    "fetch_if_empty":1,
                    "insert_after": "driver_id",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "column_4_official_papers",
                    "fieldtype": "Column Break",
                    "insert_after": "driving_license",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "driving_license_issue_date",
                    "label": _("Issue Date"),
                    "fieldtype": "Date",
                    "fetch_from":"driver_id.issuing_date",
                    "fetch_if_empty":1,
                    "insert_after": "column_4_official_papers",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "driving_license_expiry_date",
                    "label": _("Expiry Date"),
                    "fieldtype": "Date",
                    "fetch_from":"driver_id.expiry_date",
                    "fetch_if_empty":1,
                    "insert_after": "driving_license_issue_date",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "official_papers_section_5",
                    "label": _("Vehicle Information"),
                    "fieldtype": "Section Break",
                    "insert_after": "driving_license_expiry_date",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "license_plate",
                    "label": _("License Plate"),
                    "fieldtype": "Link",
                    "options": "Vehicle",
                    "insert_after": "official_papers_section_5",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "column_5_official_papers",
                    "fieldtype": "Column Break",
                    "insert_after": "driving_license",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "vehicle_make",
                    "label": _("Make"),
                    "fieldtype": "Data",
                    "fetch_from":"license_plate.make",
                    "fetch_if_empty":1,
                    "insert_after": "column_5_official_papers",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "column_6_official_papers",
                    "fieldtype": "Column Break",
                    "insert_after": "vehicle_make",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "vehicle_model",
                    "label": _("Model"),
                    "fieldtype": "Data",
                    "fetch_from":"license_plate.model",
                    "fetch_if_empty":1,
                    "insert_after": "column_6_official_papers",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "official_papers_section_6",
                    "label": _("Additional Information"),
                    "fieldtype": "Section Break",
                    "insert_after": "vehicle_model",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "exit_permit_required",
                    "label": _("Exit Permit Required"),
                    "fieldtype": "Check",
                    "insert_after": "official_papers_section_6",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "end_of_service_benefit_paid",
                    "label": _("50% End Of Service Benefit Paid"),
                    "fieldtype": "Check",
                    "insert_after": "exit_permit_required",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "column_7_official_papers",
                    "fieldtype": "Column Break",
                    "insert_after": "end_of_service_benefit_paid",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "hiring_source",
                    "label": _("Hiring Source"),
                    "fieldtype": "Data",
                    "insert_after": "column_7_official_papers",
                    "module": "Sabaa"
                },
                {
                    "fieldname": "last_air_ticket_paid_by_company",
                    "label": _("Last Air Ticket Paid By Company"),
                    "fieldtype": "Check",
                    "insert_after": "hiring_source",
                    "module": "Sabaa"
                },
            ],
        }

        create_custom_fields(custom_fields, ignore_validate=True, update=True)
    

    except Exception:
        frappe.log_error("Patch Error: Add Custom Fields", frappe.get_traceback())
        raise