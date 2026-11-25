import frappe
from frappe.desk.query_report import run

frappe.init(site="mysite2.localhost", sites_path=".")
frappe.connect()
f = {"company": "Sumit", "from_date": "2026-04-01", "to_date": "2026-11-04"}
for user in ("Administrator", "warehouse.exec@freshindia.example"):
	frappe.set_user(user)
	frappe.local.role_permissions = {}
	res = run("Stock Balance", filters=f)
	print(user, "rows:", len(res.get("result") or []), "| message:", res.get("message"))
frappe.set_user("Administrator")
print(frappe.get_all("Stock Ledger Entry", {"company": "Sumit", "is_cancelled": 0}, ["count(name) as n"]) if False else
	frappe.db.count("Stock Ledger Entry", {"company": "Sumit", "is_cancelled": 0}))
frappe.destroy()
