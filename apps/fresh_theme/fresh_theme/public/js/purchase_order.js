// Draft Purchase Orders: hide the Attachments panel and the activity / change-history timeline
// until the PO is submitted (the server also refuses uploads and skips Version records).
// Submitted Purchase Orders: a "Goods Receipt" panel showing ordered / accepted / rejected / pending.
frappe.ui.form.on("Purchase Order", {
	refresh(frm) {
		const draft = frm.doc.docstatus === 0;
		$(frm.wrapper).toggleClass("fi-draft-po", draft);
		if (draft && !frm.is_new()) {
			frm.set_intro(
				__("Draft: attachments and change history are switched off. They turn on once this Purchase Order is submitted."),
				"orange"
			);
		}
		if (frm.doc.docstatus === 1) fresh_theme.po_receipt.render(frm);
	},
});

frappe.provide("fresh_theme.po_receipt");

Object.assign(fresh_theme.po_receipt, {
	async render(frm) {
		const { message: s } = await frappe.call({
			method: "fresh_theme.purchase_order.get_receipt_status",
			args: { purchase_order: frm.doc.name },
		});
		if (!s || frm.doc.docstatus !== 1) return;
		// v16 keeps frm.dashboard under the Connections tab - show this at the top of the Details tab instead
		$(frm.wrapper).find(".fi-rcv-section").remove();
		const $first = $(frm.fields_dict.supplier.wrapper).closest(".form-section");
		$(`<div class="form-section card-section fi-rcv-section">
			<div class="section-head">${__("Goods Receipt")}</div>
			<div class="section-body">${this.panel(s)}</div>
		</div>`).insertBefore($first);
		this.mark_rows(frm, s);
	},

	pct(part, whole) {
		return whole > 0 ? Math.min(100, (part / whole) * 100) : 0;
	},

	bar(r) {
		const a = this.pct(r.accepted, r.ordered);
		const j = Math.min(this.pct(r.rejected, r.ordered), 100 - a);
		const p = Math.min(this.pct(r.pending, r.ordered), 100 - a - j);
		return `<div class="fi-rcv-bar">
			<span class="acc" style="width:${a}%"></span><span class="rej" style="width:${j}%"></span><span class="pen" style="width:${p}%"></span>
		</div>`;
	},

	state(r) {
		if (r.pending <= 0) return r.rejected > 0 ? ["done-rej", __("Received (with rejection)")] : ["done", __("Fully received")];
		if (r.received > 0) return ["part", __("Partly received")];
		return ["none", __("Not received")];
	},

	panel(s) {
		const n = (v) => format_number(v, null, 2).replace(/\.00$/, "");
		const closed = ["Closed", "Completed"].includes(s.status);
		const head = s.pending > 0
			? closed
				? `<b>${n(s.pending)}</b> ${__("short-closed, will not be received")}`
				: `<b>${n(s.pending)}</b> ${__("still to be received - Purchase Order stays open")}`
			: __("All ordered quantity has been received");
		const kpi = (cls, label, v) => `<div class="fi-rcv-kpi ${cls}"><div class="v">${n(v)}</div><div class="l">${label}</div></div>`;

		const rows = s.items.map((r) => {
			const [cls, label] = this.state(r);
			return `<tr class="fi-rcv-${cls}">
				<td class="idx">${r.idx}</td>
				<td><div class="nm">${frappe.utils.escape_html(r.item_name || r.item_code)}</div><div class="cd">${frappe.utils.escape_html(r.item_code)}</div></td>
				<td class="bar-cell">${this.bar(r)}<div class="tag">${label}</div></td>
				<td class="r">${n(r.ordered)}</td>
				<td class="r acc">${n(r.accepted)}</td>
				<td class="r rej">${r.rejected ? n(r.rejected) : "-"}</td>
				<td class="r pen">${r.pending ? n(r.pending) : "-"}</td>
				<td class="uom">${frappe.utils.escape_html(r.uom || "")}</td>
			</tr>`;
		}).join("");

		const receipts = s.receipts.length
			? s.receipts.map((r) => `<a class="fi-rcv-chip ${r.is_return ? "ret" : ""}" href="/app/purchase-receipt/${encodeURIComponent(r.name)}">
				${r.is_return ? __("Return") : ""} ${frappe.utils.escape_html(r.name)} · ${frappe.datetime.str_to_user(r.posting_date)}
				· <b>${n(r.accepted)}</b> ${__("accepted")}${r.rejected ? `, <b>${n(r.rejected)}</b> ${__("rejected")}` : ""}</a>`).join("")
			: `<span class="fi-rcv-none">${__("No Purchase Receipt yet")}</span>`;

		return `<div class="fi-rcv">
			<div class="fi-rcv-top">
				<div class="fi-rcv-ring" style="--p:${this.pct(s.ordered - s.pending, s.ordered)}">
					<span>${Math.floor(this.pct(s.ordered - s.pending, s.ordered))}%</span>
				</div>
				<div class="fi-rcv-head">
					<div class="t">${head}</div>
					${this.bar(s)}
					<div class="fi-rcv-legend"><i class="acc"></i>${__("Accepted")}<i class="rej"></i>${__("Rejected")}<i class="pen"></i>${__("Pending")}</div>
				</div>
				<div class="fi-rcv-kpis">
					${kpi("ord", __("Ordered"), s.ordered)}${kpi("acc", __("Accepted"), s.accepted)}
					${kpi("rej", __("Rejected"), s.rejected)}${kpi("pen", __("Pending"), s.pending)}
				</div>
			</div>
			<table class="fi-rcv-items">
				<thead><tr><th>#</th><th>${__("Item")}</th><th>${__("Progress")}</th><th class="r">${__("Ordered")}</th>
				<th class="r">${__("Accepted")}</th><th class="r">${__("Rejected")}</th><th class="r">${__("Pending")}</th><th>${__("UOM")}</th></tr></thead>
				<tbody>${rows}</tbody>
			</table>
			<div class="fi-rcv-receipts"><span class="lbl">${__("Receipts")}</span>${receipts}</div>
		</div>`;
	},

	// colour the Items table rows too: amber = pending, green = fully received
	mark_rows(frm, s) {
		const by_idx = Object.fromEntries(s.items.map((r) => [r.idx, r]));
		(frm.fields_dict.items.grid.grid_rows || []).forEach((gr) => {
			const r = by_idx[gr.doc.idx];
			if (!r) return;
			$(gr.row).removeClass("fi-row-pending fi-row-part fi-row-done")
				.addClass(r.pending <= 0 ? "fi-row-done" : r.received > 0 ? "fi-row-part" : "fi-row-pending")
				.attr("title", r.pending > 0 ? __("{0} {1} pending", [r.pending, r.uom]) : __("Fully received"));
		});
	},
});
