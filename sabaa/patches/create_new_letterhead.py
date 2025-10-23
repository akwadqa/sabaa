import frappe

def execute():
    if not frappe.db.exists("Letter Head", "Sabaa"):
        frappe.get_doc({
            "doctype": "Letter Head",
            "letter_head_name": "Sabaa",
            "is_default": 1,
            "content": """
<style>
    .header-img {
        display: block;
        width: 100%;
        height: 100%;
        margin: 0 auto;
        margin-bottom: 25px;
    }
    
    .print-format img {
        max-width:none;
    }
    
    .print-format {
        padding-top:10px;    
    }
</style>

<img class="header-img" src="{{ frappe.utils.get_url() }}/files/saba-letterhead.jpg">
""",
            "source": "HTML",
            "align": "Left",
            "is_default": 1,
            "disabled": 0
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.msgprint("✅ Sabaa Letter Head created successfully!")
    else:
        frappe.msgprint("ℹ️ Sabaa Letter Head already exists — skipped.")
