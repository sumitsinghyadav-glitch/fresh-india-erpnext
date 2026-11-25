import frappe

LOGO = "/assets/fresh_theme/images/fresh-logo.png"
ICON = "/assets/fresh_theme/images/fresh-icon.png"


def after_install():
	apply_branding()


def apply_branding():
	"""Point the desk, login page and browser tab at the Fresh India logo."""
	ws = frappe.get_single("Website Settings")
	ws.app_name = "Fresh India ERP"
	ws.app_logo = LOGO
	ws.splash_image = LOGO
	ws.favicon = ICON
	ws.save()

	nb = frappe.get_single("Navbar Settings")
	nb.app_logo = LOGO
	nb.save()
	frappe.db.commit()
	frappe.clear_cache()
