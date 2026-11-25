"""Test the Warehouse Executive role as a real user: allowed activities work, everything else is refused,
and no other role lost access on the doctypes that got custom permissions. Re-runnable."""

import frappe
from frappe.utils import add_days, nowdate

from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

ROLE, USER = "Warehouse Executive", "warehouse.exec@freshindia.example"
COMPANY, WH = "Sumit", "Stores - Ssy"
CUSTOMER = "Gurugram Tech Solutions Pvt Ltd"
results = []


def check(name, fn, expect_ok=True):
	try:
		out = fn()
		ok = expect_ok
		detail = out if isinstance(out, str) else ""
	except frappe.PermissionError as e:
		ok, detail = not expect_ok, f"refused: {str(e)[:90]}"
	except Exception as e:  # noqa: BLE001
		ok, detail = False, f"{type(e).__name__}: {str(e)[:160]}"
	frappe.db.rollback() if not ok else frappe.db.commit()
	results.append(ok)
	print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def ensure_user():
	if not frappe.db.exists("User", USER):
		u = frappe.get_doc({"doctype": "User", "email": USER, "first_name": "Warehouse", "last_name": "Executive",
			"send_welcome_email": 0, "new_password": frappe.generate_hash(length=20), "roles": [{"role": ROLE}]})
		u.insert(ignore_permissions=True)
	roles = set(frappe.get_roles(USER)) - {"All", "Guest", "Desk User"}
	assert roles == {ROLE}, roles
	frappe.db.commit()


def as_user(fn):
	def run():
		frappe.set_user(USER)
		try:
			return fn()
		finally:
			frappe.set_user("Administrator")
	return run


def pick_stock_item():
	return frappe.db.sql("""select b.item_code from tabBin b join tabItem i on i.name=b.item_code
		where b.warehouse=%s and b.actual_qty>=5 and i.has_serial_no=0 and i.has_batch_no=0 and i.is_stock_item=1
		and exists (select 1 from `tabItem Price` p where p.item_code=i.name and p.selling=1)
		order by b.actual_qty desc limit 1""", WH)[0][0]


# ---------------------------------------------------------------- allowed
def stock_inward_from_po():
	po = STATE["po"]  # raised by purchase (Administrator); the executive only receives it
	pr = make_purchase_receipt(po)
	pr.posting_date, pr.set_posting_time = nowdate(), 1
	pr.insert()
	pr.submit()
	return f"{pr.name} from {po}"


def stock_inward_material_receipt():
	se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": COMPANY,
		"items": [{"item_code": STATE["item"], "qty": 10, "t_warehouse": WH, "basic_rate": 100}]})
	se.insert()
	se.submit()
	return se.name


def stock_transfer():
	target = frappe.db.sql("""select name from tabWarehouse where company=%s and is_group=0 and disabled=0
		and name!=%s and ifnull(warehouse_type, '')!='Transit' and is_rejected_warehouse=0 order by name limit 1""",
		(COMPANY, WH))[0][0]
	se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Transfer", "company": COMPANY,
		"items": [{"item_code": STATE["item"], "qty": 2, "s_warehouse": WH, "t_warehouse": target}]})
	se.insert()
	se.submit()
	STATE["transfer"] = se.name
	return f"{se.name}: {WH} -> {target}"


def cancel_and_amend_transfer():
	se = frappe.get_doc("Stock Entry", STATE["transfer"])
	se.cancel()
	amended = frappe.copy_doc(se)
	amended.amended_from = se.name
	amended.items[0].qty = 1
	amended.insert()
	amended.submit()
	return f"cancelled {se.name}, amended -> {amended.name}"


def delete_draft():
	se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Transfer", "company": COMPANY,
		"items": [{"item_code": STATE["item"], "qty": 1, "s_warehouse": WH,
			"t_warehouse": frappe.db.get_value("Stock Entry Detail", {"parent": STATE["transfer"]}, "t_warehouse")}]})
	se.insert()
	frappe.delete_doc("Stock Entry", se.name)
	return f"draft {se.name} deleted"


def sales_order_to_invoice():
	so = frappe.get_doc({"doctype": "Sales Order", "company": COMPANY, "customer": CUSTOMER, "transaction_date": nowdate(),
		"delivery_date": add_days(nowdate(), 3), "set_warehouse": WH,
		"items": [{"item_code": STATE["item"], "qty": 2, "warehouse": WH, "delivery_date": add_days(nowdate(), 3)}]})
	so.insert()
	so.submit()
	dn = make_delivery_note(so.name)
	dn.insert()
	dn.submit()
	si = make_sales_invoice(dn.name)
	si.insert()
	si.submit()
	STATE.update(si=si.name, dn=dn.name)
	return f"{so.name} -> {dn.name} -> {si.name} (Rs {si.grand_total:,.2f})"


def e_invoice_and_e_waybill_rights():
	# India Compliance's generate_e_invoice / generate_e_waybill first check these exact permissions
	frappe.has_permission("Sales Invoice", "submit", throw=True)
	frappe.has_permission("Delivery Note", "submit", throw=True)
	frappe.has_permission("e-Waybill Log", "print", throw=True)
	frappe.has_permission("e-Invoice Log", "read", throw=True)
	frappe.get_list("e-Waybill Log", limit=1)
	return "submit on SI/DN + e-Waybill/e-Invoice log access OK (live API call not made)"


def run_and_export_reports():
	from frappe.desk.query_report import run
	from frappe.permissions import can_export
	out = []
	for r, f in (("Stock Balance", {"company": COMPANY, "from_date": "2026-04-01", "to_date": nowdate()}),
			("Stock Ledger", {"company": COMPANY, "from_date": "2026-10-01", "to_date": nowdate()}),
			("Sales Register", {"company": COMPANY, "from_date": "2026-04-01", "to_date": nowdate()}),
			("Delivery Note Trends", {"company": COMPANY, "period": "Monthly", "based_on": "Item", "fiscal_year": "2026-2027",
				"period_based_on": "posting_date"}),
			("Sales Order Analysis", {"company": COMPANY, "from_date": "2026-04-01", "to_date": nowdate()})):
		res = run(r, filters=f)
		ref = frappe.db.get_value("Report", r, "ref_doctype")
		can_export(ref, raise_exception=True)
		out.append(f"{r}={len(res.get('result') or [])} rows")
	# e-Invoice Summary is granted too, but the report itself refuses to run while e-Invoice is disabled in GST Settings
	frappe.has_permission("Report", doc="e-Invoice Summary", throw=True)
	return ", ".join(out)


# ---------------------------------------------------------------- refused
def create_purchase_order():
	frappe.get_doc({"doctype": "Purchase Order", "company": COMPANY, "supplier": "Redington India Ltd",
		"schedule_date": nowdate(), "items": [{"item_code": STATE["item"], "qty": 1, "rate": 1, "schedule_date": nowdate()}]}).insert()


def create_payment_entry():
	frappe.new_doc("Payment Entry").update({"company": COMPANY, "payment_type": "Receive", "party_type": "Customer",
		"party": CUSTOMER, "paid_amount": 1, "received_amount": 1}).insert()


def create_journal_entry():
	frappe.new_doc("Journal Entry").update({"company": COMPANY, "posting_date": nowdate()}).insert()


def edit_item_master():
	item = frappe.get_doc("Item", STATE["item"])
	item.description = (item.description or "") + " "
	item.save()


def edit_price_list_rate():
	ip = frappe.get_doc("Item Price", frappe.db.get_value("Item Price", {"item_code": STATE["item"]}))
	ip.price_list_rate += 1
	ip.save()


def open_general_ledger():
	from frappe.desk.query_report import run
	run("General Ledger", filters={"company": COMPANY, "from_date": "2026-04-01", "to_date": nowdate(), "group_by": "Group by Voucher (Consolidated)"})


# ---------------------------------------------------------------- other roles untouched
def regression():
	bad = []
	for dt in frappe.get_all("Custom DocPerm", {"role": ROLE}, pluck="parent"):
		std = {(p.role, p.permlevel, p.if_owner, tuple(p.get(f) for f in PT)) for p in frappe.get_all("DocPerm", {"parent": dt}, ["*"])}
		cus = {(p.role, p.permlevel, p.if_owner, tuple(p.get(f) for f in PT)) for p in frappe.get_all("Custom DocPerm",
			{"parent": dt, "role": ["!=", ROLE]}, ["*"])}
		if not std <= cus:
			bad.append(dt)
	return bad


PT = ("select", "read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "print", "email", "share")
STATE = {}

frappe.init(site="mysite2.localhost", sites_path=".")
frappe.connect()
frappe.set_user("Administrator")
try:
	ensure_user()
	STATE["item"] = pick_stock_item()
	from erpnext.controllers.accounts_controller import get_taxes_and_charges
	po = frappe.get_doc({"doctype": "Purchase Order", "company": COMPANY, "supplier": "Redington India Ltd",
		"transaction_date": nowdate(), "schedule_date": nowdate(), "set_warehouse": WH, "tax_category": "In-State",
		"supplier_address": "Redington India Ltd-Billing", "billing_address": "Sumit-Billing", "shipping_address": "Sumit-Billing",
		"taxes_and_charges": "Input GST In-state - Ssy",
		"taxes": get_taxes_and_charges("Purchase Taxes and Charges Template", "Input GST In-state - Ssy"),
		"items": [{"item_code": STATE["item"], "qty": 20, "rate": 210, "schedule_date": nowdate(), "warehouse": WH}]})
	po.insert()
	po.submit()
	STATE["po"] = po.name
	frappe.db.commit()
	print("Stock Balance prepared_report:", frappe.db.get_value("Report", "Stock Balance", "prepared_report"))
	print("user:", USER, "roles:", sorted(set(frappe.get_roles(USER)) - {"All", "Guest", "Desk User"}), "item:", STATE["item"], "\n")
	print("-- allowed")
	check("Stock inward: Purchase Receipt from open PO", as_user(stock_inward_from_po))
	check("Stock inward: Material Receipt", as_user(stock_inward_material_receipt))
	check("Stock transfer to other warehouse", as_user(stock_transfer))
	check("Cancel + amend own transfer (full rights)", as_user(cancel_and_amend_transfer))
	check("Delete a draft (full rights)", as_user(delete_draft))
	check("Sales Order -> Delivery Note -> Sales Invoice", as_user(sales_order_to_invoice))
	check("e-Invoice / e-Way Bill rights", as_user(e_invoice_and_e_waybill_rights))
	check("Run + export reports", as_user(run_and_export_reports))
	print("\n-- refused (outside the role)")
	check("Create Purchase Order", as_user(create_purchase_order), expect_ok=False)
	check("Create Payment Entry", as_user(create_payment_entry), expect_ok=False)
	check("Create Journal Entry", as_user(create_journal_entry), expect_ok=False)
	check("Edit Item master", as_user(edit_item_master), expect_ok=False)
	check("Change Item Price", as_user(edit_price_list_rate), expect_ok=False)
	check("Open General Ledger report", as_user(open_general_ledger), expect_ok=False)
	print("\n-- other roles")
	bad = regression()
	results.append(not bad)
	print(("PASS" if not bad else "FAIL") + "  every standard permission rule still present on the customised doctypes", bad or "")
	print(f"\n{sum(results)}/{len(results)} passed")
finally:
	frappe.destroy()
