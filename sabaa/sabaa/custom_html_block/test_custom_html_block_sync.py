# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from sabaa.sabaa.custom_html_block import BLOCKS_DIRECTORY, STANDARD_BLOCKS, sync_custom_html_blocks

BLOCK_NAME = "HR Dashboard"
FOLDER = STANDARD_BLOCKS[BLOCK_NAME]


class TestCustomHTMLBlockSync(FrappeTestCase):
	def setUp(self):
		self._savepoint = "test_custom_html_block_sync"
		frappe.db.savepoint(self._savepoint)
		self.addCleanup(lambda: frappe.db.rollback(save_point=self._savepoint))

	def test_creates_missing_block_from_files(self):
		frappe.delete_doc("Custom HTML Block", BLOCK_NAME, force=True, ignore_missing=True)

		sync_custom_html_blocks()

		self.assert_block_matches_files()

	def test_restores_block_edited_in_desk(self):
		sync_custom_html_blocks()
		frappe.db.set_value(
			"Custom HTML Block", BLOCK_NAME, {"html": "<p>edited</p>", "script": "", "private": 1}
		)

		sync_custom_html_blocks()

		self.assert_block_matches_files()

	def test_workspace_references_synced_block(self):
		workspace = frappe.get_doc("Workspace", "HR Dashboard")

		self.assertEqual(workspace.module, "Sabaa")
		self.assertIn(BLOCK_NAME, [row.custom_block_name for row in workspace.custom_blocks])

	def assert_block_matches_files(self):
		block = frappe.get_doc("Custom HTML Block", BLOCK_NAME)
		source = BLOCKS_DIRECTORY / FOLDER

		self.assertEqual(block.html, (source / f"{FOLDER}.html").read_text())
		self.assertEqual(block.script, (source / f"{FOLDER}.js").read_text())
		self.assertEqual(block.style, (source / f"{FOLDER}.css").read_text())
		self.assertEqual(block.private, 0)
