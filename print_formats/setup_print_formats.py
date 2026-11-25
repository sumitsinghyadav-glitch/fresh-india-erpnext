"""Install the "Fresh India" Sales Order / Sales Invoice print formats on mysite2.localhost.

Expects next to this file (in /home/frappe/scripts/pf/): fresh_india.html, fresh_india.css, logo_src.webp
Re-runnable: updates the formats in place. Writes sample PDFs to /home/frappe/scripts/pf/out/.
"""

import base64
import io
import os

import frappe
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
COMPANY = "Sumit"
FORMATS = {
    "Sales Order": "Fresh India Sales Order",
    "Sales Invoice": "Fresh India Sales Invoice",
    "Purchase Order": "Fresh India Purchase Order",
}
TEMPLATES = {"Sales Order": "fresh_india.html", "Sales Invoice": "fresh_india.html", "Purchase Order": "fresh_india_po.html"}
MODULES = {"Sales Order": "Selling", "Sales Invoice": "Accounts", "Purchase Order": "Buying"}


def logo_png():
    """webp -> trimmed PNG (wkhtmltopdf cannot render webp)."""
    img = Image.open(os.path.join(HERE, "logo_src.webp")).convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(bg, img).convert("RGB")
    # bounding box of non-white pixels
    mask = flat.point(lambda p: 255 if p < 245 else 0).convert("L")
    flat = flat.crop(mask.getbbox())
    flat.thumbnail((360, 360), Image.LANCZOS)
    buf = io.BytesIO()
    flat.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def main():
    frappe.init(site="mysite2.localhost", sites_path=".")
    frappe.connect()
    frappe.set_user("Administrator")

    png = logo_png()
    data_uri = "data:image/png;base64," + base64.b64encode(png).decode()

    # Logo as a public file + company logo
    file_url = frappe.db.get_value("File", {"file_name": "fresh-india-show-logo.png"}, "file_url")
    if not file_url:
        f = frappe.get_doc({"doctype": "File", "file_name": "fresh-india-show-logo.png", "content": png, "is_private": 0,
                            "attached_to_doctype": "Company", "attached_to_name": COMPANY})
        f.insert()
        file_url = f.file_url
    frappe.db.set_value("Company", COMPANY, {
        "company_logo": file_url, "phone_no": "+91 124 456 7890",
        "email": "sales@sumit-trading.example", "website": "www.sumit-trading.example",
    })

    # Company bank account (shown on invoices)
    if not frappe.db.exists("Bank", "HDFC Bank"):
        frappe.get_doc({"doctype": "Bank", "bank_name": "HDFC Bank"}).insert()
    if not frappe.db.exists("Bank Account", {"company": COMPANY, "is_company_account": 1}):
        frappe.get_doc({
            "doctype": "Bank Account", "account_name": "Sumit Current A/c", "bank": "HDFC Bank",
            "company": COMPANY, "is_company_account": 1, "is_default": 1, "account": "HDFC Bank - Ssy",
            "bank_account_no": "50200012345678", "branch_code": "HDFC0000123",
        }).insert()

    css = open(os.path.join(HERE, "fresh_india.css")).read()
    for doctype, name in FORMATS.items():
        html = open(os.path.join(HERE, TEMPLATES[doctype])).read().replace("__LOGO__", data_uri)
        pf = frappe.get_doc("Print Format", name) if frappe.db.exists("Print Format", name) else frappe.new_doc("Print Format")
        pf.update({
            "name": name, "doc_type": doctype, "module": MODULES[doctype],
            "standard": "No", "custom_format": 1, "print_format_type": "Jinja", "disabled": 0,
            "html": html, "css": css, "font_size": 0, "margin_top": 8, "margin_bottom": 8, "margin_left": 6, "margin_right": 6,
        })
        pf.save() if not pf.is_new() else pf.insert()
        frappe.make_property_setter(
            {"doctype": doctype, "doctype_or_field": "DocType", "property": "default_print_format", "value": name},
            is_system_generated=False,
        )
    frappe.db.commit()
    frappe.clear_cache()
    print("formats installed, logo", file_url, len(png), "bytes")

    # A draft invoice to demo the proforma: the 3 back-ordered printers of SO-00015
    draft_si = frappe.db.get_value("Sales Invoice", {"company": COMPANY, "docstatus": 0, "remarks": "Proforma demo"})
    if not draft_si:
        from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

        si = make_sales_invoice("SAL-ORD-2026-00015")
        si.remarks = "Proforma demo"
        si.insert()
        frappe.db.commit()
        draft_si = si.name

    # Sample PDFs
    out = os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    samples = [("Sales Invoice", "SINV-26-00002"), ("Sales Invoice", "SINV-26-00001"), ("Sales Invoice", "SINV-26-00008"),
               ("Sales Invoice", "SINV-26-00006"), ("Sales Invoice", "SINV-26-00011-1"),
               ("Sales Order", "SAL-ORD-2026-00008"), ("Sales Order", "SAL-ORD-2026-00009"), ("Sales Order", "SAL-ORD-2026-00013"),
               ("Sales Invoice", draft_si),
               ("Purchase Order", "PUR-ORD-2026-00012"), ("Purchase Order", "PUR-ORD-2026-00011")]
    for dt, dn in samples:
        pdf = frappe.get_print(dt, dn, FORMATS[dt], as_pdf=True, no_letterhead=1)
        with open(os.path.join(out, f"{dn}.pdf"), "wb") as fh:
            fh.write(pdf)
        print("pdf", dn, len(pdf))
    frappe.destroy()


main()
