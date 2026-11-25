"""Read-only export of UI customizations from a Frappe site into JSON files (one per doctype).
Usage (inside the bench container, from frappe-bench/sites):
    ../env/bin/python export_customizations.py <site> <out_dir>
"""
import json
import os
import sys

import frappe

SITE, OUT = sys.argv[1], sys.argv[2]

# doctype -> filters selecting only user-made (non-standard) records
TARGETS = {
	"Custom Field": {},
	"Property Setter": {},
	"Client Script": {},
	"Server Script": {},
	"Custom DocPerm": {},
	"Role": {"is_custom": 1},
	"Role Profile": {},
	"Module Profile": {},
	"Print Format": {"standard": "No"},
	"Letter Head": {},
	"Report": {"is_standard": "No"},
	"Workflow": {},
	"Workflow State": {},
	"Workflow Action Master": {},
	"Notification": {"is_standard": 0},
	"Workspace": {"public": 1, "module": ["is", "not set"]},
	"Number Card": {"is_standard": 0},
	"Dashboard Chart": {"is_standard": 0},
	"Dashboard": {"is_standard": 0},
	"Custom HTML Block": {},
	"Web Form": {"is_standard": 0},
}

SKIP_KEYS = {"modified_by", "owner", "creation", "modified", "idx", "lft", "rgt", "_user_tags", "_comments", "_assign", "_liked_by"}


def clean(d):
	if isinstance(d, dict):
		return {k: clean(v) for k, v in d.items() if k not in SKIP_KEYS}
	if isinstance(d, list):
		return [clean(x) for x in d]
	return d


frappe.init(SITE, sites_path=".")
frappe.connect()
os.makedirs(OUT, exist_ok=True)
summary = {}
for doctype, filters in TARGETS.items():
	if not frappe.db.exists("DocType", doctype):
		continue
	meta = frappe.get_meta(doctype)
	filters = {k: v for k, v in filters.items() if meta.has_field(k)}
	names = frappe.get_all(doctype, filters=filters, pluck="name", order_by="name asc")
	if not names:
		continue
	docs = [clean(frappe.get_doc(doctype, n).as_dict(no_default_fields=False)) for n in names]
	fname = frappe.scrub(doctype) + ".json"
	with open(os.path.join(OUT, fname), "w") as f:
		json.dump(docs, f, indent=1, sort_keys=True, default=str)
	summary[doctype] = len(docs)
frappe.destroy()
print(json.dumps(summary, indent=1))
