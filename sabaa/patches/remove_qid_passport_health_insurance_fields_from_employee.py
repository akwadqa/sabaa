import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

# Custom fields fully replaced by Employee Reference records.
CUSTOM_FIELDS_TO_DELETE = [
    # QID
    "custom_employee_qid",
    "qid_file",
    "qid_expiry",
    # Passport (custom)
    "passport_file",
    # Health Insurance
    "official_papers_section_3",
    "insured",
    "health_certificate_issue_date",
    "column_3_official_papers",
    "health_insurance_expiry",
    "health_insurance_file",
    "health_insurance_provider",
    # Driving License
    "driving_license",
    "driving_license_issue_date",
    "driving_license_expiry_date",
]

NATIVE_FIELDS_TO_HIDE = [
    "passport_details_section",
    "passport_number",
    "valid_upto",
    "column_break_73",
    "date_of_issue",
    "place_of_issue",
]


def execute():
    try:
  
        REANCHOR_BEFORE_DELETE = {
            "column_1_official_papers": "nationality",
            "official_papers_section_2": "nationality_ar",
            "official_papers_section_4": "place_of_work_ar",
            "health_insurance_no": "health_insurance_section",
            "column_4_official_papers": "driver_id",
            "official_papers_section_5": "column_4_official_papers",
            "column_5_official_papers": "license_plate",
        }
        for fieldname, new_insert_after in REANCHOR_BEFORE_DELETE.items():
            if frappe.db.exists("Custom Field", f"Employee-{fieldname}"):
                frappe.db.set_value(
                    "Custom Field",
                    f"Employee-{fieldname}",
                    "insert_after",
                    new_insert_after,
                )

        if frappe.db.exists("Custom Field", "Employee-health_insurance_no"):
            frappe.db.set_value(
                "Custom Field",
                "Employee-health_insurance_no",
                "depends_on",
                "",
            )

        for fieldname in CUSTOM_FIELDS_TO_DELETE:
            frappe.delete_doc(
                "Custom Field",
                f"Employee-{fieldname}",
                ignore_missing=True,
                ignore_permissions=True,
            )

        for fieldname in NATIVE_FIELDS_TO_HIDE:
            make_property_setter("Employee", fieldname, "hidden", "1", "Check")

    except Exception:
        frappe.log_error(
            "Patch Error: Remove QID/Passport/Health Insurance Fields", frappe.get_traceback()
        )
        raise
