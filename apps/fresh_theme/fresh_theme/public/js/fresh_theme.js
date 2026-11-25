// Fresh India ERP - small desk touches (branding only; no business logic)
(() => {
	const BRAND = "Fresh India ERP";

	// browser tab title: "<page> · Fresh India ERP"
	const setTitle = () => {
		const t = document.title || "";
		if (t && !t.endsWith(BRAND)) {
			document.title = t.replace(/\s*[|·-]\s*(Frappe|ERPNext).*$/i, "") + " · " + BRAND;
		}
	};

	$(document).on("page-change", () => setTimeout(setTitle, 300));
	$(document).ready(() => setTimeout(setTitle, 500));
})();
