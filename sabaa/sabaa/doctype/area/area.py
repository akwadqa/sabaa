# Copyright (c) 2025, Akwad Programming and contributors
# For license information, please see license.txt

from frappe.utils.nestedset import NestedSet


class Area(NestedSet):
	nsm_parent_field = "parent_area"
