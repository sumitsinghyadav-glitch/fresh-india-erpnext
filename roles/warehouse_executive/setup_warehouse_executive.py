"""Role 'Warehouse Executive': stock inward, stock transfer, sales order -> delivery -> invoice, e-Invoice / e-Way Bill,
stock & sales reports. Re-runnable. Also writes an Excel permission matrix and Data Import files to EXPORT_DIR.

Permissions are added the way the Role Permission Manager does it (frappe.permissions.add_permission), which first
copies a doctype's standard rules into Custom DocPerm - so no other role loses access.
"""

import csv
import os

import frappe
from frappe.core.doctype.data_import.exporter import Exporter
from frappe.permissions import add_permission, setup_custom_perms

ROLE = "Warehouse Executive"
EXPORT_DIR = "/home/frappe/scripts/exports/warehouse_executive"

PTYPES = ["select", "read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "print", "email", "share"]
FULL = {"select", "read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "print", "email", "share"}
EDIT = {"select", "read", "write", "create", "report", "export", "print", "email"}
VIEW = {"select", "read", "report", "export", "print"}
PICK = {"select", "read"}

# (activity, doctype, rights)
DOCTYPES = [
	("Stock Inward", "Purchase Receipt", FULL),
	("Stock Inward / Transfer", "Stock Entry", FULL),
	("Stock Inward / Transfer", "Serial and Batch Bundle", FULL),
	("Stock Inward / Transfer", "Batch", EDIT),
	("Sales Order Processing", "Sales Order", FULL),
	("Sales Order Processing", "Pick List", FULL),
	("Sales Order Processing", "Packing Slip", FULL),
	("Sales Order Processing", "Delivery Note", FULL),
	("Invoicing", "Sales Invoice", FULL),
	("e-Invoice / e-Way Bill", "e-Waybill Log", VIEW),
	("e-Invoice / e-Way Bill", "e-Invoice Log", VIEW),
	("Masters (customer side)", "Address", EDIT),
	("Masters (customer side)", "Contact", EDIT),
	("Reference (read only)", "Purchase Order", VIEW),
	("Reference (read only)", "Material Request", VIEW),
	("Reference (read only)", "Stock Ledger Entry", VIEW),
	("Reference (read only)", "Bin", VIEW),
	("Reference (read only)", "Stock Reservation Entry", VIEW),
	("Reference (read only)", "Serial No", VIEW),
	("Reference (read only)", "Item", VIEW),
	("Reference (read only)", "Item Price", VIEW),
	("Reference (read only)", "Product Bundle", VIEW),
	("Reference (read only)", "Warehouse", VIEW),
	("Reference (read only)", "Customer", VIEW),
	("Reference (read only)", "Supplier", VIEW),
	("Reference (read only)", "Stock Entry Type", PICK),
	("Reference (read only)", "Price List", PICK),
	("Reference (read only)", "Pricing Rule", PICK),
	("Reference (read only)", "UOM", PICK),
	("Reference (read only)", "Item Group", PICK),
	("Reference (read only)", "Brand", PICK),
	("Reference (read only)", "Company", PICK),
	("Reference (read only)", "Sales Taxes and Charges Template", PICK),
	("Reference (read only)", "Purchase Taxes and Charges Template", PICK),
	("Reference (read only)", "Item Tax Template", PICK),
	("Reference (read only)", "Shipping Rule", PICK),
	("Reference (read only)", "Cost Center", PICK),
	("Reference (read only)", "Account", PICK),
	("Reference (read only)", "Terms and Conditions", PICK),
	("Reference (read only)", "Payment Terms Template", PICK),
	("Reference (read only)", "Customer Group", PICK),
	("Reference (read only)", "Territory", PICK),
	("Reference (read only)", "Sales Person", PICK),
	("Reference (read only)", "Driver", PICK),
	("Reference (read only)", "Vehicle", PICK),
	("Reference (read only)", "GSTIN", PICK),
]

REPORTS = [
	# stock
	"Stock Balance", "Stock Ledger", "Stock Projected Qty", "Stock Ageing", "Warehouse wise Item Balance Age and Value",
	"Warehouse Wise Stock Balance", "Item Balance (Simple)", "Total Stock Summary", "Stock Analytics", "Item Shortage Report",
	"Batch-Wise Balance History", "Available Batch Report", "Batch Item Expiry Status", "Serial No Ledger", "Reserved Stock",
	"Purchase Receipt Trends", "Delivery Note Trends", "Delayed Order Report", "Delayed Item Report",
	# sales
	"Sales Order Analysis", "Sales Order Trends", "Item-wise Sales History", "Sales Analytics",
	"Sales Register", "Item-wise Sales Register", "Sales Invoice Trends", "Delivered Items To Be Billed",
	# GST
	"e-Invoice Summary",
]

ALWAYS_HELD = {"All", "Desk User"}  # roles every desk user already has


def held_rights(doctype):
	"""Rights a new desk user already gets on this doctype from roles everyone has."""
	have = set()
	for p in frappe.get_meta(doctype).permissions:
		if p.role in ALWAYS_HELD and not p.permlevel and not p.if_owner:
			have |= {pt for pt in PTYPES if p.get(pt)}
	return have


def ensure_role():
	if not frappe.db.exists("Role", ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": ROLE, "desk_access": 1,
			"home_page": "/app/stock"}).insert(ignore_permissions=True)


def grant(doctype, rights):
	meta = frappe.get_meta(doctype)
	if not meta.is_submittable:
		rights = rights - {"submit", "cancel", "amend"}
	if rights <= held_rights(doctype):
		return "already open to all desk users"
	setup_custom_perms(doctype)  # copy standard rules first, as the Role Permission Manager does
	if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": ROLE, "permlevel": 0, "if_owner": 0}):
		add_permission(doctype, ROLE, 0)
	name = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": ROLE, "permlevel": 0, "if_owner": 0})
	frappe.db.set_value("Custom DocPerm", name, {pt: int(pt in rights) for pt in PTYPES})
	frappe.clear_cache(doctype=doctype)
	return "granted"


def allow_report(report):
	"""Custom Role on a report REPLACES its standard role list, so carry those roles over and add ours."""
	if not frappe.db.exists("Report", report):
		return "missing"
	name = frappe.db.get_value("Custom Role", {"report": report})
	doc = frappe.get_doc("Custom Role", name) if name else frappe.get_doc({"doctype": "Custom Role", "report": report,
		"ref_doctype": frappe.db.get_value("Report", report, "ref_doctype"),
		"roles": [{"role": r} for r in frappe.get_all("Has Role", {"parent": report, "parenttype": "Report"}, pluck="role")]})
	if ROLE not in [r.role for r in doc.roles]:
		doc.append("roles", {"role": ROLE})
	doc.save(ignore_permissions=True)
	return "allowed"


# ---------------------------------------------------------------- exports
def export_files(results, report_results):
	from openpyxl import Workbook
	from openpyxl.styles import Alignment, Font, PatternFill

	os.makedirs(EXPORT_DIR, exist_ok=True)
	head_fill, head_font = PatternFill("solid", fgColor="1F7A33"), Font(bold=True, color="FFFFFF")
	yes_fill = PatternFill("solid", fgColor="E3F4E6")

	def sheet(ws, header, rows, widths):
		ws.append(header)
		for c in ws[1]:
			c.fill, c.font, c.alignment = head_fill, head_font, Alignment(horizontal="center", wrap_text=True)
		for r in rows:
			ws.append(r)
		for i, w in enumerate(widths, 1):
			ws.column_dimensions[ws.cell(1, i).column_letter].width = w
		ws.freeze_panes = "B2" if len(header) > 6 else "A2"
		for row in ws.iter_rows(min_row=2):
			for c in row:
				if c.value == "Yes":
					c.fill, c.alignment = yes_fill, Alignment(horizontal="center")

	wb = Workbook()
	ws = wb.active
	ws.title = "Activities"
	sheet(ws, ["Activity", "What the Warehouse Executive can do", "Documents"], [
		["Stock Inward", "Receive goods from suppliers (from PO) and Material Receipt into any warehouse / location",
			"Purchase Receipt, Stock Entry (Material Receipt)"],
		["Stock Transfer", "Move stock between warehouses / locations", "Stock Entry (Material Transfer)"],
		["Sales Order Processing", "Create & submit Sales Orders, pick, pack and deliver",
			"Sales Order, Pick List, Packing Slip, Delivery Note"],
		["Invoicing", "Create & submit Sales Invoices against deliveries / orders", "Sales Invoice"],
		["e-Invoice", "Generate / cancel IRN on Sales Invoice (needs Submit on Sales Invoice + e-Invoice enabled in GST Settings)",
			"Sales Invoice, e-Invoice Log"],
		["e-Way Bill", "Generate / update / cancel e-Way Bill on Delivery Note & Sales Invoice (needs Submit on the document)",
			"Delivery Note, Sales Invoice, e-Waybill Log"],
		["Reports", f"{len(REPORTS)} stock, sales and GST reports with Excel/CSV export", "see 'Reports' sheet"],
		["Rights", "Full rights on transactions: create, submit, cancel, amend, delete. Masters are read-only "
			"(except customer Address / Contact).", ""],
	], [24, 80, 50])

	ws = wb.create_sheet("Doctype Permissions")
	rows = []
	for activity, dt, _rights in DOCTYPES:
		effective = results[dt]["rights"]
		rows.append([dt, activity, frappe.get_meta(dt).module, results[dt]["status"]]
			+ ["Yes" if pt in effective else "" for pt in PTYPES])
	sheet(ws, ["DocType", "Activity", "Module", "Status"] + [pt.title() for pt in PTYPES], rows, [30, 26, 14, 28] + [9] * len(PTYPES))

	ws = wb.create_sheet("Reports")
	rows = []
	for r in REPORTS:
		rep = frappe.db.get_value("Report", r, ["module", "ref_doctype", "report_type"], as_dict=True) or {}
		roles = frappe.get_all("Has Role", {"parenttype": "Custom Role", "parent": frappe.db.get_value("Custom Role", {"report": r})},
			pluck="role")
		rows.append([r, rep.get("module"), rep.get("report_type"), rep.get("ref_doctype"), report_results[r], "Yes", ", ".join(sorted(roles))])
	sheet(ws, ["Report", "Module", "Type", "Based on", "Status", "Export", "Roles allowed"], rows, [42, 12, 16, 24, 10, 8, 90])

	ws = wb.create_sheet("How to import")
	for line in IMPORT_STEPS:
		ws.append([line])
	ws.column_dimensions["A"].width = 140
	wb.save(f"{EXPORT_DIR}/Warehouse_Executive_Permission_Matrix.xlsx")

	# Data Import files, produced by Frappe's own exporter so the columns match the importer exactly
	def write_csv(fname, doctype, fields, filters):
		e = Exporter(doctype, export_fields=fields, export_data=True, export_filters=filters, file_type="CSV")
		with open(f"{EXPORT_DIR}/{fname}", "w", newline="", encoding="utf-8") as f:
			csv.writer(f).writerows(e.get_csv_array_for_export())

	perm_fields = {"Custom DocPerm": ["parent", "role", "permlevel", "if_owner", *PTYPES, "import"]}
	granted = [dt for dt, r in results.items() if r["status"] == "granted"]
	write_csv("2_Custom_DocPerm_Warehouse_Executive.csv", "Custom DocPerm", perm_fields,
		{"role": ROLE, "parent": ["in", granted]})
	write_csv("3_Custom_DocPerm_baseline_other_roles.csv", "Custom DocPerm", perm_fields,
		{"role": ["!=", ROLE], "parent": ["in", granted]})
	write_csv("4_Custom_Role_report_access.csv", "Custom Role",
		{"Custom Role": ["report", "ref_doctype"], "Has Role": ["role"]},
		{"report": ["in", [r for r in REPORTS if report_results[r] == "allowed"]]})
	with open(f"{EXPORT_DIR}/1_Role_and_README.txt", "w", encoding="utf-8") as f:
		f.write("\n".join(IMPORT_STEPS) + "\n\nDoctypes in file 3 (baseline):\n" + "\n".join(f"  - {d}" for d in granted) + "\n")


IMPORT_STEPS = [
	"How to recreate the Warehouse Executive role on another site (Frappe / ERPNext v16 + India Compliance)",
	"",
	"1. Create the Role by hand (Role cannot be loaded through Data Import): Role List > Add Role > Role Name 'Warehouse Executive',",
	"   tick 'Desk Access', Home Page '/app/stock'. Save.",
	"2. Check the baseline (IMPORTANT): once a DocType has ANY row in Custom DocPerm, Frappe ignores its standard permissions.",
	"   For every DocType listed in file 3, open Role Permission Manager on the target site:",
	"   - if it already shows customised rules (a 'Reset to defaults' button is visible), skip that DocType's rows in file 3;",
	"   - if it does not, import that DocType's rows from file 3 FIRST, so existing roles keep their access.",
	"   (Alternative to file 3: in Role Permission Manager open the DocType and use 'Add A New Rule' for Warehouse Executive -",
	"    the UI copies the standard rules automatically - then tick the boxes as per the Excel matrix.)",
	"3. Data Import > New > Document Type 'Custom DocPerm', Import Type 'Insert New Records', upload",
	"   2_Custom_DocPerm_Warehouse_Executive.csv. Start Import.",
	"4. Report access: Data Import > 'Custom Role', 'Insert New Records', upload 4_Custom_Role_report_access.csv.",
	"   If the target already has a Custom Role for a report, use 'Update Existing Records' for that report or add the role",
	"   in the existing Custom Role by hand (a Custom Role replaces the report's standard role list).",
	"5. Assign the role: User > Roles > tick 'Warehouse Executive'. No User Permissions are needed: the role works across all",
	"   warehouses / locations. e-Invoice also needs 'Enable e-Invoice' in GST Settings.",
	"6. Clear cache (or log out / in) and test with a Warehouse Executive user.",
	"",
	"Rollback on the target site: delete the Custom DocPerm rows with Role = Warehouse Executive, remove the role from the",
	"Custom Role records, then delete the Role.",
]


def main():
	frappe.init(site="mysite2.localhost", sites_path=".")
	frappe.connect()
	frappe.set_user("Administrator")
	try:
		ensure_role()
		results = {}
		for _activity, dt, rights in DOCTYPES:
			status = grant(dt, rights)
			effective = rights if status == "granted" else held_rights(dt)
			if not frappe.get_meta(dt).is_submittable:
				effective = effective - {"submit", "cancel", "amend"}
			results[dt] = {"status": status, "rights": effective}
			print(f"{status:32} {dt}")
		report_results = {r: allow_report(r) for r in REPORTS}
		print("reports:", report_results)
		frappe.db.commit()
		frappe.clear_cache()
		export_files(results, report_results)
		print("exports:", sorted(os.listdir(EXPORT_DIR)))
	finally:
		frappe.destroy()


main()
