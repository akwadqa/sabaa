"""Version-controlled Custom HTML Blocks.

Frappe cannot export Custom HTML Block as a standard document, so each block keeps
its HTML, JavaScript and CSS in a folder next to this module. `sync_custom_html_blocks`
writes the files to the database after each migrate. The files are the source of
truth: changes made to these blocks through Desk are overwritten on the next migrate.
"""

from pathlib import Path

import frappe

BLOCKS_DIRECTORY = Path(__file__).parent

# Block name -> folder that holds <folder>.html, <folder>.js and <folder>.css
STANDARD_BLOCKS = {
	"HR Dashboard": "hr_dashboard",
}


def sync_custom_html_blocks() -> None:
	for block_name, folder in STANDARD_BLOCKS.items():
		sync_custom_html_block(block_name, folder)


def sync_custom_html_block(block_name: str, folder: str) -> None:
	source = BLOCKS_DIRECTORY / folder
	values = {
		"html": (source / f"{folder}.html").read_text(),
		"script": (source / f"{folder}.js").read_text(),
		"style": (source / f"{folder}.css").read_text(),
		"private": 0,
	}

	if not frappe.db.exists("Custom HTML Block", block_name):
		frappe.get_doc({"doctype": "Custom HTML Block", "name": block_name, **values}).insert()
		return

	block = frappe.get_doc("Custom HTML Block", block_name)
	block.update(values)
	block.save()
