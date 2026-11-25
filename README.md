# Fresh India ERPNext

ERPNext setup and UI for the Fresh India site: desk / login theme, print formats, and the customizations made in
the ERPNext UI (custom fields, form changes, roles, permissions, workflow, letterheads, reports).

Built on **Frappe / ERPNext v16** (v16.50.0) with **HRMS** and **India Compliance**, running on
[frappe_docker](https://github.com/frappe/frappe_docker).

## What's here

```
apps/fresh_theme/            Frappe app: Fresh India desk + login look (green dock, mint sidebar, orange actions, logo)
print_formats/               Fresh India Sales Order / Sales Invoice / Purchase Order print formats + setup script
customizations/              UI customizations exported from the site (one JSON array per doctype)
roles/warehouse_executive/   Warehouse Executive role: setup + test scripts and the permission matrix (CSV / XLSX)
docker/                      Image build file for the theme, compose override, start script, example env
export_customizations.py     Read-only script that produced customizations/
```

### customizations/

| File | Count | What |
|---|---|---|
| custom_field.json | 77 | Fields added in the UI (fields created by India Compliance are left out; it adds them on install) |
| property_setter.json | 375 | Form / field property changes (labels, hidden, mandatory, defaults ...) |
| custom_docperm.json | 796 | Role permissions per doctype |
| role.json, role_profile.json | 1, 6 | Custom role (Employee Self Service) and role profiles |
| workflow*.json | 1 + 7 + 7 | Hostel Registration workflow with its states and actions |
| client_script.json, server_script.json | 1, 1 | Scripts used by the Hostel workflow (server scripts must be enabled on the site) |
| print_format.json | 4 | Fresh India SO / SI / PO and IRS 1099 |
| letter_head.json | 2 | Company Letterhead (+ Grey) |
| report.json | 2 | GST Tax Invoice-wise, GST Tax Rate-wise (query reports on Purchase Invoice) |
| notification.json | 2 | Error Log, Integration Request notifications |

## Install the theme

On any v16 bench:

```bash
git clone <this-repo-url> fresh-india-erpnext
cp -r fresh-india-erpnext/apps/fresh_theme <bench>/apps/
cd <bench> && ./env/bin/pip install -e apps/fresh_theme && echo fresh_theme >> sites/apps.txt
bench --site <site> install-app fresh_theme
bench build --app fresh_theme
```

After editing CSS / JS, bump `THEME_VERSION` in `apps/fresh_theme/fresh_theme/hooks.py` so browsers reload it.

With Docker: `docker/Containerfile.theme` adds the app on top of an ERPNext v16 + HRMS + India Compliance image.
Build it from a folder where the app sits at `apps/fresh_theme` (change the `FROM` line to your base image).

## Apply the print formats

Copy `print_formats/` into the backend container and run `setup_print_formats.py` with the bench Python. It creates
or updates the formats (re-runnable). Set `COMPANY` at the top of the script to your company name.

## Apply the UI customizations

Review the JSON first (it targets this site's company and masters). Then import a file with:

```bash
bench --site <site> import-doc customizations/custom_field.json
```

Suggested order: role, role_profile, custom_field, property_setter, custom_docperm, workflow_state,
workflow_action_master, workflow, client_script, server_script, letter_head, print_format, report, notification.
Take a site backup before importing (`bench --site <site> backup`).

To refresh the export from a running site (read-only):

```bash
docker cp export_customizations.py <backend-container>:/tmp/
docker exec -w /home/frappe/frappe-bench/sites <backend-container> \
  /home/frappe/frappe-bench/env/bin/python /tmp/export_customizations.py <site> /tmp/fx
docker cp <backend-container>:/tmp/fx/. customizations/
```

## Run locally with Docker (as on the original PC)

`docker/bench2.ps1` starts the stack from a frappe_docker clone placed next to this folder, using
`docker/compose.bench2.yaml` and an env file. Copy `bench2.example.env` to `bench2.env` and set `DB_PASSWORD`.
Site: `mysite2.localhost`, port 8081.

## Not included

No database, business data, passwords or API keys. Demo-data scripts and the RentBook / Store Vision apps are kept
in a separate private repo.
