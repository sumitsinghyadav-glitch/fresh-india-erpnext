"""Draft Purchase Orders: no attachments and no audit trail until the PO is submitted.
Submitted Purchase Orders: receipt progress (ordered / accepted / rejected / pending) for the form."""

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def get_receipt_status(purchase_order):
	"""Per-item receipt progress of a submitted PO, in the PO's UOM.
	ERPNext counts accepted + rejected as 'received' on the PO, so pending = ordered - received."""
	po = frappe.get_doc("Purchase Order", purchase_order)
	po.check_permission("read")

	pri = frappe.qb.DocType("Purchase Receipt Item")
	pr = frappe.qb.DocType("Purchase Receipt")
	rows = (
		frappe.qb.from_(pri)
		.join(pr).on(pr.name == pri.parent)
		.select(pri.purchase_order_item, pri.parent, pr.posting_date, pr.is_return,
			pri.qty, pri.rejected_qty, pri.conversion_factor, pri.stock_qty)
		.where((pr.docstatus == 1) & (pri.purchase_order == po.name))
		.orderby(pr.posting_date).orderby(pr.creation)
		.run(as_dict=True)
	)

	items, by_row = [], {}
	for d in po.items:
		row = by_row[d.name] = frappe._dict(
			idx=d.idx, item_code=d.item_code, item_name=d.item_name, uom=d.uom,
			ordered=flt(d.qty), received=flt(d.received_qty), accepted=0.0, rejected=0.0,
		)
		items.append(row)

	receipts = {}
	for r in rows:
		row = by_row.get(r.purchase_order_item)
		if not row:
			continue
		row.accepted += flt(r.qty)
		row.rejected += flt(r.rejected_qty)
		rec = receipts.setdefault(r.parent, frappe._dict(name=r.parent, posting_date=r.posting_date,
			is_return=r.is_return, accepted=0.0, rejected=0.0))
		rec.accepted += flt(r.qty)
		rec.rejected += flt(r.rejected_qty)

	for row in items:
		row.pending = max(row.ordered - row.received, 0)

	total = lambda key: sum(r[key] for r in items)  # noqa: E731
	return {
		"status": po.status,
		"per_received": flt(po.per_received),
		"ordered": total("ordered"),
		"accepted": total("accepted"),
		"rejected": total("rejected"),
		"pending": total("pending"),
		"items": items,
		"receipts": list(receipts.values()),
	}


def skip_draft_version(doc, method=None):
	"""before_save (runs only for plain saves, i.e. docstatus 0): don't record a Version for draft edits.
	Submit / cancel / update-after-submit don't run before_save, so their history is kept."""
	if doc.docstatus == 0:
		doc.flags.ignore_version = True


def block_draft_attachment(doc, method=None):
	"""File.before_insert: refuse sidebar attachments on a draft Purchase Order."""
	if doc.attached_to_doctype != "Purchase Order" or not doc.attached_to_name or doc.attached_to_field:
		return  # not a PO, or a file uploaded into a field (e.g. an image in Terms) - allowed

	po = frappe.db.get_value("Purchase Order", doc.attached_to_name, ["docstatus", "amended_from"], as_dict=True)
	if not po or po.docstatus != 0:
		return

	# amending a cancelled PO copies its attachments onto the new draft - let those through
	if po.amended_from and frappe.db.exists(
		"File",
		{"attached_to_doctype": "Purchase Order", "attached_to_name": po.amended_from, "file_url": doc.file_url},
	):
		return

	frappe.throw(
		_("Attachments can be added once Purchase Order {0} is submitted.").format(frappe.bold(doc.attached_to_name)),
		title=_("Draft Purchase Order"),
	)
