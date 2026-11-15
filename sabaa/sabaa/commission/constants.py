from enum import StrEnum

COMMISSION_MANAGER = "Commission Manager"


class Category(StrEnum):
	TRADITIONAL_TRADE = "Traditional Trade"
	MODERN_TRADE = "Modern Trade"
	SALES_MANAGEMENT = "Sales Management"
	SMILE24 = "Smile24"
	LOGISTICS = "Logistics"
	TENDERS = "Tenders"


class LineStatus(StrEnum):
	READY = "Ready"
	NEEDS_SETUP = "Needs setup"
	WAITING = "Waiting for business input"
	MISSING_DATA = "Missing data"
	NOT_ASSIGNED = "Not assigned"
