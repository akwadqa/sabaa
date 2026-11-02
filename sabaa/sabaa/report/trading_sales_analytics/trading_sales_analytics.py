# Copyright (c) 2026, Akwad Programming and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.query_builder import Criterion, DocType
from frappe.query_builder.functions import IfNull
from frappe.utils import add_days, add_to_date, flt, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimension_with_children
from erpnext.accounts.utils import get_fiscal_year
from sabaa.utils import format_quantity_by_uoms, get_uom_conversion_map


def execute(filters=None):
    return Analytics(filters).run()


class Analytics:
    def __init__(self, filters=None):
        self.filters = frappe._dict(filters or {})
        self.date_field = (
            "transaction_date"
            if self.filters.doc_type in ["Sales Order", "Purchase Order"]
            else "posting_date"
        )
        self.months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        self.customer_groups = get_dimension_with_children("Customer Group", self.filters.customer_group or [])
        self.sales_persons = get_dimension_with_children("Sales Person", self.filters.sales_person or [])
        self.get_period_date_ranges()

    def update_company_list_for_parent_company(self):
        company_list = [self.filters.get("company")]

        selected_company = self.filters.get("company")
        if (
            selected_company
            and self.filters.get("show_aggregate_value_from_subsidiary_companies")
            and frappe.db.get_value("Company", selected_company, "is_group")
        ):
            lft, rgt = frappe.db.get_value("Company", selected_company, ["lft", "rgt"])
            child_companies = frappe.db.get_list(
                "Company", filters={"lft": [">", lft], "rgt": ["<", rgt]}, pluck="name"
            )

            company_list.extend(child_companies)

        self.filters["company"] = company_list

    def run(self):
        self.update_company_list_for_parent_company()
        self.get_columns()
        self.get_data()
        self.get_chart_data()

        # Skipping total row for tree-view reports
        skip_total_row = 0

        if self.filters.tree_type in [
            "Supplier Group",
            "Item Group",
            "Customer Group",
            "Territory",
            "Sales Person",
        ]:
            skip_total_row = 1

        return self.columns, self.data, None, self.chart, None, skip_total_row

    def get_columns(self):
        if self.filters.tree_type in ["Customer", "Supplier", "Item"]:
            self.columns = [
                 {
                    "label": _(self.filters.tree_type),
                    "options": self.filters.tree_type,
                    "fieldname": "entity",
                    "fieldtype": "Link" ,
                    "hidden": 1
                },
                {
                    "label": _(self.filters.tree_type + " Name"),
                    "fieldname": "entity_name",
                    "fieldtype": "Data",
                    "width": 400,
                }            
            ]
        else:
            self.columns = [
                {
                    "label": _(self.filters.tree_type),
                    "options": self.filters.tree_type if self.filters.tree_type != "Order Type" else "",
                    "fieldname": "entity",
                    "fieldtype": "Link" if self.filters.tree_type != "Order Type" else "Data",
                    "width": 300 if self.filters.tree_type != "Order Type" else 200,
                }
		    ]                 

        if self.filters.tree_type == "Item":
            self.columns.append(
                {
                    "label": _("UOM"),
                    "fieldname": "stock_uom",
                    "fieldtype": "Link",
                    "options": "UOM",
                    "width": 100,
                }
            )

        fieldtype = "Float"

        if (
            self.filters.tree_type == "Item"
            and self.filters.value_quantity == "Quantity"
        ):
            fieldtype = "Data"

        for end_date in self.periodic_daterange:
            period = self.get_period(end_date)
            self.columns.append(
                {"label": _(period), "fieldname": scrub(period), "fieldtype": fieldtype, "width": 200}
            )

        total_fieldtype = "Float"

        if (
            self.filters.tree_type == "Item"
            and self.filters.value_quantity == "Quantity"
        ):
            total_fieldtype = "Data"

        self.columns.append({
            "label": _("Total"),
            "fieldname": "total",
            "fieldtype": total_fieldtype,
            "width": 200
        })

    def get_data(self):
        if self.filters.tree_type in ["Customer", "Supplier"]:
            self.get_sales_transactions_based_on_customers_or_suppliers()
            self.get_rows()

        elif self.filters.tree_type == "Item":
            self.get_sales_transactions_based_on_items()
            self.get_rows()

        elif self.filters.tree_type in ["Customer Group", "Supplier Group", "Territory"]:
            self.get_sales_transactions_based_on_customer_or_territory_group()
            self.get_rows_by_group()

        elif self.filters.tree_type == "Item Group":
            self.get_sales_transactions_based_on_item_group()
            self.get_rows_by_group()

        elif self.filters.tree_type == "Sales Person":
            self.get_sales_transactions_based_on_sales_person()
            self.get_rows_by_group()

        elif self.filters.tree_type == "Order Type":
            if self.filters.doc_type != "Sales Order":
                self.data = []
                return
            self.get_sales_transactions_based_on_order_type()
            self.get_rows_by_group()

        elif self.filters.tree_type == "Project":
            self.get_sales_transactions_based_on_project()
            self.get_rows()

    def get_sales_transactions_based_on_order_type(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_total"
        else:
            value_field = "total_qty"

        doctype = DocType(self.filters.doc_type)

        self.entries = (
            frappe.qb.from_(doctype)
            .select(
                doctype.order_type.as_("entity"),
                doctype[self.date_field],
                doctype[value_field].as_("value_field"),
            )
            .where(
                Criterion.all(
                    [
                        doctype.docstatus == 1,
                        doctype.company.isin(self.filters.company),
                        doctype[self.date_field].between(self.filters.from_date, self.filters.to_date),
                        IfNull(doctype.order_type, "") != "",
                        *self.get_document_conditions(doctype),
                    ]
                )
            )
            .orderby(doctype.order_type)
        ).run(as_dict=True)

        self.get_teams()

    def get_sales_transactions_based_on_customers_or_suppliers(self):
        party = "customer" if self.filters.tree_type == "Customer" else "supplier"
        doctype = DocType(self.filters.doc_type)

        self.entries = (
            frappe.qb.from_(doctype)
            .select(
                doctype[party].as_("entity"),
                doctype[f"{party}_name"].as_("entity_name"),
                doctype[self.get_document_value_field()].as_("value_field"),
                doctype[self.date_field],
            )
            .where(self.get_document_filters(doctype))
        ).run(as_dict=True)

        self.entity_names = {}
        for d in self.entries:
            self.entity_names.setdefault(d.entity, d.entity_name)

    def get_sales_transactions_based_on_items(self):
        selected_uom = self.filters.get("uom")

        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_amount"
        else:
            value_field = "stock_qty"

        doctype = DocType(self.filters.doc_type)
        doctype_item = DocType(f"{self.filters.doc_type} Item")

        query = (
            frappe.qb.from_(doctype_item)
            .join(doctype)
            .on(doctype.name == doctype_item.parent)
            .select(
                doctype_item.item_code.as_("entity"),
                doctype_item.item_name.as_("entity_name"),
                doctype_item.stock_uom,
                doctype_item[value_field].as_("value_field"),
                doctype[self.date_field],
            )
            .where(
                Criterion.all(
                    [
                        doctype_item.docstatus == 1,
                        doctype.company.isin(self.filters.company),
                        doctype[self.date_field].between(self.filters.from_date, self.filters.to_date),
                        *self.get_document_conditions(doctype),
                    ]
                )
            )
        )        

        self.entries = query.run(as_dict=True)

        # Build UOM conversion map per item
        self.item_uom_map = {}

        item_codes = {d.entity for d in self.entries}

        for item_code in item_codes:
            uom_map = get_uom_conversion_map(item_code)
            self.item_uom_map[item_code] = uom_map

        self.entity_names = {}
        for d in self.entries:
            self.entity_names.setdefault(d.entity, d.entity_name)

    def get_sales_transactions_based_on_customer_or_territory_group(self):
        if self.filters.tree_type == "Customer Group":
            entity_field = "customer_group"
        elif self.filters.tree_type == "Supplier Group":
            entity_field = "supplier"
            self.get_supplier_parent_child_map()
        else:
            entity_field = "territory"

        doctype = DocType(self.filters.doc_type)

        self.entries = (
            frappe.qb.from_(doctype)
            .select(
                doctype[entity_field].as_("entity"),
                doctype[self.get_document_value_field()].as_("value_field"),
                doctype[self.date_field],
            )
            .where(self.get_document_filters(doctype))
        ).run(as_dict=True)
        self.get_groups()

    def get_sales_transactions_based_on_item_group(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_amount"
        else:
            value_field = "qty"

        doctype = DocType(self.filters.doc_type)
        doctype_item = DocType(f"{self.filters.doc_type} Item")

        self.entries = (
            frappe.qb.from_(doctype_item)
            .join(doctype)
            .on(doctype.name == doctype_item.parent)
            .select(
                doctype_item.item_group.as_("entity"),
                doctype_item[value_field].as_("value_field"),
                doctype[self.date_field],
            )
            .where(
                Criterion.all(
                    [
                        doctype_item.docstatus == 1,
                        doctype.company.isin(self.filters.company),
                        doctype[self.date_field].between(self.filters.from_date, self.filters.to_date),
                        *self.get_document_conditions(doctype),
                    ]
                )
            )
        ).run(as_dict=True)

        self.get_groups()

    def get_sales_transactions_based_on_sales_person(self):
        doctype = DocType(self.filters.doc_type)
        sales_team = DocType("Sales Team")

        query = (
            frappe.qb.from_(doctype)
            .join(sales_team)
            .on((sales_team.parent == doctype.name) & (sales_team.parenttype == self.filters.doc_type))
            .select(
                sales_team.sales_person.as_("entity"),
                (doctype[self.get_document_value_field()] * sales_team.allocated_percentage / 100).as_(
                    "value_field"
                ),
                doctype[self.date_field],
            )
            .where(self.get_document_filters(doctype, include_sales_person=False))
        )

        # Filter the team rows directly so only the selected sales persons' shares are counted
        if self.sales_persons:
            query = query.where(sales_team.sales_person.isin(self.sales_persons))

        self.entries = query.run(as_dict=True)
        self.get_groups()

    def get_sales_transactions_based_on_project(self):
        doctype = DocType(self.filters.doc_type)

        self.entries = (
            frappe.qb.from_(doctype)
            .select(
                doctype.project.as_("entity"),
                doctype[self.get_document_value_field()].as_("value_field"),
                doctype[self.date_field],
            )
            .where(self.get_document_filters(doctype) & (doctype.project != ""))
        ).run(as_dict=True)

    def get_document_value_field(self):
        return "base_net_total" if self.filters.value_quantity == "Value" else "total_qty"

    def get_document_filters(self, doctype, include_sales_person=True):
        """Filters for document-level queries; unlike item-level queries, these also exclude opening entries."""
        conditions = [
            doctype.docstatus == 1,
            doctype.company.isin(self.filters.company),
            doctype[self.date_field].between(self.filters.from_date, self.filters.to_date),
            *self.get_document_conditions(doctype, include_sales_person),
        ]

        if self.filters.doc_type in ["Sales Invoice", "Purchase Invoice", "Payment Entry"]:
            conditions.append(doctype.is_opening == "No")

        return Criterion.all(conditions)

    def get_document_conditions(self, doctype, include_sales_person=True) -> list:
        """Customer Group and Sales Person filter conditions on the parent document."""
        conditions = []

        if self.customer_groups:
            conditions.append(doctype.customer_group.isin(self.customer_groups))

        if include_sales_person and self.sales_persons:
            # A subquery, not a join, so a document with several matching sales persons is counted once
            sales_team = DocType("Sales Team")
            conditions.append(
                doctype.name.isin(
                    frappe.qb.from_(sales_team)
                    .select(sales_team.parent)
                    .where(
                        (sales_team.parenttype == self.filters.doc_type)
                        & sales_team.sales_person.isin(self.sales_persons)
                    )
                )
            )

        return conditions

    def get_rows(self):
        self.data = []
        self.get_periodic_data()

        for entity, period_data in self.entity_periodic_data.items():
            row = {
                "entity": entity,
                "entity_name": f"<a href='{frappe.utils.get_url_to_form(self.filters.tree_type, entity)}' target='_blank'>{self.entity_names.get(entity)}</a>" if hasattr(self, "entity_names") else None,
            }
            total = 0
            for end_date in self.periodic_daterange:
                period = self.get_period(end_date)
                amount = flt(period_data.get(period, 0.0))

                # Format quantity by UOM only for Item + Quantity mode
                if (
                    self.filters.tree_type == "Item"
                    and self.filters.value_quantity == "Quantity"
                ):
                    conversions = self.item_uom_map.get(entity, {})
                    stock_uom = period_data.get("stock_uom")
                    display_value = format_quantity_by_uoms(
                        amount,
                        conversions,
                        stock_uom
                    )
                    row[scrub(period)] = display_value
                else:
                    row[scrub(period)] = amount

                total += amount

            if (
                self.filters.tree_type == "Item"
                and self.filters.value_quantity == "Quantity"
            ):
                conversions = self.item_uom_map.get(entity, {})
                stock_uom = period_data.get("stock_uom")
                row["total"] = format_quantity_by_uoms(
                    total,
                    conversions,
                    stock_uom
                )
            else:
                row["total"] = total

            if self.filters.tree_type == "Item":
                row["stock_uom"] = period_data.get("stock_uom")

            self.data.append(row)

    def get_rows_by_group(self):
        self.get_periodic_data()
        out = []

        for d in reversed(self.group_entries):
            row = {"entity": d.name, "indent": self.depth_map.get(d.name)}
            total = 0
            for end_date in self.periodic_daterange:
                period = self.get_period(end_date)
                amount = flt(self.entity_periodic_data.get(d.name, {}).get(period, 0.0))
                row[scrub(period)] = amount
                if d.parent and (self.filters.tree_type != "Order Type" or d.parent == "Order Types"):
                    self.entity_periodic_data.setdefault(d.parent, frappe._dict()).setdefault(period, 0.0)
                    self.entity_periodic_data[d.parent][period] += amount
                total += amount

            row["total"] = total
            out = [row, *out]

        if self.is_tree_filtered:
            out = [row for row in out if flt(row["total"])]

        self.data = out

    @property
    def is_tree_filtered(self):
        """True when the tree type's own filter is set, so unselected (all-zero) nodes are noise."""
        return (self.filters.tree_type == "Sales Person" and bool(self.sales_persons)) or (
            self.filters.tree_type == "Customer Group" and bool(self.customer_groups)
        )

    def get_periodic_data(self):
        self.entity_periodic_data = frappe._dict()

        for d in self.entries:
            if self.filters.tree_type == "Supplier Group":
                d.entity = self.parent_child_map.get(d.entity)
            period = self.get_period(d.get(self.date_field))
            self.entity_periodic_data.setdefault(d.entity, frappe._dict()).setdefault(period, 0.0)
            self.entity_periodic_data[d.entity][period] += flt(d.value_field)

            if self.filters.tree_type == "Item":
                self.entity_periodic_data[d.entity]["stock_uom"] = d.stock_uom

    def get_period(self, posting_date):
        if self.filters.range == "Weekly":
            period = _("Week {0} {1}").format(str(posting_date.isocalendar()[1]), str(posting_date.year))
        elif self.filters.range == "Monthly":
            period = _(str(self.months[posting_date.month - 1])) + " " + str(posting_date.year)
        elif self.filters.range == "Quarterly":
            period = _("Quarter {0} {1}").format(
                str(((posting_date.month - 1) // 3) + 1), str(posting_date.year)
            )
        else:
            year = get_fiscal_year(posting_date, company=self.filters.company[0])
            period = str(year[0])
        return period

    def get_period_date_ranges(self):
        from dateutil.relativedelta import MO, relativedelta

        from_date, to_date = getdate(self.filters.from_date), getdate(self.filters.to_date)

        increment = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Yearly": 12}.get(self.filters.range, 1)

        if self.filters.range in ["Monthly", "Quarterly"]:
            from_date = from_date.replace(day=1)
        elif self.filters.range == "Yearly":
            from_date = get_fiscal_year(from_date)[1]
        else:
            from_date = from_date + relativedelta(from_date, weekday=MO(-1))

        self.periodic_daterange = []
        for _dummy in range(1, 53):
            if self.filters.range == "Weekly":
                period_end_date = add_days(from_date, 6)
            else:
                period_end_date = add_to_date(from_date, months=increment, days=-1)

            if period_end_date > to_date:
                period_end_date = to_date

            self.periodic_daterange.append(period_end_date)

            from_date = add_days(period_end_date, 1)
            if period_end_date == to_date:
                break

    def get_groups(self):
        if self.filters.tree_type == "Territory":
            parent = "parent_territory"
        if self.filters.tree_type == "Customer Group":
            parent = "parent_customer_group"
        if self.filters.tree_type == "Item Group":
            parent = "parent_item_group"
        if self.filters.tree_type == "Supplier Group":
            parent = "parent_supplier_group"
        if self.filters.tree_type == "Sales Person":
            parent = "parent_sales_person"

        self.depth_map = frappe._dict()

        self.group_entries = frappe.db.sql(
            f"""select name, lft, rgt , {parent} as parent
            from `tab{self.filters.tree_type}` order by lft""",
            as_dict=1,
        )

        for d in self.group_entries:
            if d.parent:
                self.depth_map.setdefault(d.name, self.depth_map.get(d.parent) + 1)
            else:
                self.depth_map.setdefault(d.name, 0)

    def get_teams(self):
        self.depth_map = frappe._dict()

        self.group_entries = frappe.db.sql(
            f""" select * from (select "Order Types" as name, 0 as lft,
            2 as rgt, '' as parent union select distinct order_type as name, 1 as lft, 1 as rgt, "Order Types" as parent
            from `tab{self.filters.doc_type}` where ifnull(order_type, '') != '') as b order by lft, name
        """,
            as_dict=1,
        )

        for d in self.group_entries:
            if d.parent:
                self.depth_map.setdefault(d.name, self.depth_map.get(d.parent) + 1)
            else:
                self.depth_map.setdefault(d.name, 0)

    def get_supplier_parent_child_map(self):
        self.parent_child_map = frappe._dict(
            frappe.db.sql(""" select name, supplier_group from `tabSupplier`""")
        )

    def get_chart_data(self):
        length = len(self.columns)

        if self.filters.tree_type in ["Customer", "Supplier"]:
            labels = [d.get("label") for d in self.columns[2 : length - 1]]
        elif self.filters.tree_type == "Item":
            labels = [d.get("label") for d in self.columns[3 : length - 1]]
        else:
            labels = [d.get("label") for d in self.columns[1 : length - 1]]
        self.chart = {"data": {"labels": labels, "datasets": []}, "type": "line"}

        if self.filters["value_quantity"] == "Value":
            self.chart["fieldtype"] = "Currency"
        else:
            self.chart["fieldtype"] = "Float"

