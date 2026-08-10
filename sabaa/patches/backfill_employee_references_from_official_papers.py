import frappe

EMPLOYEE_FIELDS = [
    "name",
    "custom_employee_qid",
    "qid_expiry",
    "qid_file",
    "passport_number",
    "date_of_issue",
    "valid_upto",
    "place_of_issue",
    "passport_file",
    "driving_license",
    "driving_license_issue_date",
    "driving_license_expiry_date",
    "insured",
    "health_certificate_issue_date",
    "health_insurance_expiry",
    "health_insurance_file"
]

PAPER_TYPES = [
    {
        "document": "QID",
        "field_map": {
            "reference_no": "custom_employee_qid",
            "expiry_date": "qid_expiry",
            "attachment": "qid_file",
        },
    },
    {
        "document": "Passport",
        "field_map": {
            "reference_no": "passport_number",
            "issue_date": "date_of_issue",
            "expiry_date": "valid_upto",
            "place_of_issue": "place_of_issue",
            "attachment": "passport_file",
        },
    },
    {
        "document": "Driving License",
        "field_map": {
            "reference_no": "driving_license",
            "issue_date": "driving_license_issue_date",
            "expiry_date": "driving_license_expiry_date",
        },
    },
    {
        "document": "Health Insurance",
        "field_map": {
            "issue_date": "health_certificate_issue_date",
            "expiry_date": "health_insurance_expiry",
            "attachment": "health_insurance_file",
        },
    },
]


def execute():
    try:
        employees = frappe.get_all("Employee", fields=EMPLOYEE_FIELDS)

        for employee in employees:
            for paper_type in PAPER_TYPES:
                values = {
                    target_field: employee.get(source_field)
                    for target_field, source_field in paper_type["field_map"].items()
                }

                if not any(values.values()):
                    continue

                if frappe.db.exists(
                    "Employee Reference",
                    {
                        "employee": employee.name,
                        "document": paper_type["document"],
                        "is_current": 1,
                    },
                ):
                    continue

                reference = frappe.new_doc("Employee Reference")
                reference.employee = employee.name
                reference.document = paper_type["document"]
                reference.is_current = 1

                for target_field, value in values.items():
                    if value:
                        reference.set(target_field, value)

                reference.insert(ignore_permissions=True)

    except Exception:
        frappe.log_error("Patch Error: Backfill Employee References", frappe.get_traceback())
        raise
