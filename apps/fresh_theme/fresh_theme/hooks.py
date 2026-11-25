app_name = "fresh_theme"
app_title = "Fresh Theme"
app_publisher = "Sumit"
app_description = "Fresh India look and feel for the Frappe / ERPNext desk"
app_email = "team@example.com"
app_license = "mit"

# bump after editing CSS/JS so browsers don't serve a cached copy
THEME_VERSION = "4"

app_include_css = [f"/assets/fresh_theme/css/fresh_theme.css?v={THEME_VERSION}"]
app_include_js = [f"/assets/fresh_theme/js/fresh_theme.js?v={THEME_VERSION}"]
web_include_css = [f"/assets/fresh_theme/css/fresh_login.css?v={THEME_VERSION}"]

app_logo_url = "/assets/fresh_theme/images/fresh-logo.png"

website_context = {
	"favicon": "/assets/fresh_theme/images/fresh-icon.png",
	"splash_image": "/assets/fresh_theme/images/fresh-logo.png",
}

after_install = "fresh_theme.install.after_install"

doctype_js = {"Purchase Order": "public/js/purchase_order.js"}
doctype_list_js = {"Purchase Order": "public/js/purchase_order_list.js"}

doc_events = {
	"Purchase Order": {"before_save": "fresh_theme.purchase_order.skip_draft_version"},
	"File": {"before_insert": "fresh_theme.purchase_order.block_draft_attachment"},
}
