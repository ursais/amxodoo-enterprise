To use this module, you need to:

1. Go to Accounting > Customers > Invoices
2. Create an invoice for the partner configured with **Addenda Kuehne Nagel**
3. Set the Customer Reference for the Purchase Order (optional; empty or
   `PO` + 4 uppercase letters + 9 digits)
4. Open the **Kuehne+Nagel Addenda** tab and fill:
   - File / Tracking Type
   - File / Tracking Number
   - Branch Centre
   - Transport Ref
5. Validate and stamp the invoice as usual

Field formats:

- **Purchase Order** (`ref`): empty, or `PO` + 4 uppercase letters + 9 digits
- **File Number**: `73` + 14 digits (16 characters, no separators)
- **Tracking Number**: 14 digits with a hyphen between digits 10 and 11
  (example: `1023950106-1815`)
- **Branch Centre**: 2 digits + 2 to 4 uppercase letters or digits
- **Transport Ref**: exactly 7 digits
