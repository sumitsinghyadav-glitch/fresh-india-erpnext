// Purchase Order list + form status pill: show how much has been received on partly received POs
// ("50% Received"). Wraps ERPNext's own indicator.
(() => {
	const settings = (frappe.listview_settings["Purchase Order"] ||= {});
	const erpnext_indicator = settings.get_indicator;

	settings.get_indicator = function (doc) {
		const per = flt(doc.per_received);
		const open = doc.docstatus === 1 && !["Closed", "On Hold", "Delivered", "Completed"].includes(doc.status);
		if (open && per > 0 && per < 100) {
			return [
				__("{0}% Received", [Math.floor(per)]),
				"orange",
				"per_received,>,0|per_received,<,100|status,!=,Closed|docstatus,=,1",
			];
		}
		return erpnext_indicator ? erpnext_indicator(doc) : null;
	};
})();
