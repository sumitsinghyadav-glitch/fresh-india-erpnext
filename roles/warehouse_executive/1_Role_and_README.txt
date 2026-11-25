How to recreate the Warehouse Executive role on another site (Frappe / ERPNext v16 + India Compliance)

1. Create the Role by hand (Role cannot be loaded through Data Import): Role List > Add Role > Role Name 'Warehouse Executive',
   tick 'Desk Access', Home Page '/app/stock'. Save.
2. Check the baseline (IMPORTANT): once a DocType has ANY row in Custom DocPerm, Frappe ignores its standard permissions.
   For every DocType listed in file 3, open Role Permission Manager on the target site:
   - if it already shows customised rules (a 'Reset to defaults' button is visible), skip that DocType's rows in file 3;
   - if it does not, import that DocType's rows from file 3 FIRST, so existing roles keep their access.
   (Alternative to file 3: in Role Permission Manager open the DocType and use 'Add A New Rule' for Warehouse Executive -
    the UI copies the standard rules automatically - then tick the boxes as per the Excel matrix.)
3. Data Import > New > Document Type 'Custom DocPerm', Import Type 'Insert New Records', upload
   2_Custom_DocPerm_Warehouse_Executive.csv. Start Import.
4. Report access: Data Import > 'Custom Role', 'Insert New Records', upload 4_Custom_Role_report_access.csv.
   If the target already has a Custom Role for a report, use 'Update Existing Records' for that report or add the role
   in the existing Custom Role by hand (a Custom Role replaces the report's standard role list).
5. Assign the role: User > Roles > tick 'Warehouse Executive'. No User Permissions are needed: the role works across all
   warehouses / locations. e-Invoice also needs 'Enable e-Invoice' in GST Settings.
6. Clear cache (or log out / in) and test with a Warehouse Executive user.

Rollback on the target site: delete the Custom DocPerm rows with Role = Warehouse Executive, remove the role from the
Custom Role records, then delete the Role.

Doctypes in file 3 (baseline):
  - Purchase Receipt
  - Stock Entry
  - Serial and Batch Bundle
  - Batch
  - Sales Order
  - Pick List
  - Packing Slip
  - Delivery Note
  - Sales Invoice
  - e-Waybill Log
  - e-Invoice Log
  - Address
  - Contact
  - Purchase Order
  - Material Request
  - Stock Ledger Entry
  - Bin
  - Stock Reservation Entry
  - Serial No
  - Item
  - Item Price
  - Product Bundle
  - Warehouse
  - Customer
  - Supplier
  - Stock Entry Type
  - Price List
  - Pricing Rule
  - UOM
  - Item Group
  - Brand
  - Company
  - Sales Taxes and Charges Template
  - Purchase Taxes and Charges Template
  - Item Tax Template
  - Shipping Rule
  - Cost Center
  - Account
  - Terms and Conditions
  - Payment Terms Template
  - Customer Group
  - Territory
  - Sales Person
  - Driver
  - Vehicle
  - GSTIN
