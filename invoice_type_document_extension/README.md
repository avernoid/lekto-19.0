# **Invoice Document Type Extension**

<img src="static/description/banner.png" width="100%" alt="Banner">

**Author**: [Ganemo](https://www.ganemo.com)

## Description
This module extends the functionality of Odoo to automatically assign Document Types and Series in Invoices and Stock Pickings. It is designed to streamline processes particularly for localizations that require strict document control, such as the Peruvian Localization.

## Key Features
- **Automatic Document Type Selection**: The system automatically selects the appropriate Document Type (e.g., Factura, Boleta, Guía de Remisión) based on the Partner's configuration or the Journal settings.
- **Series Propagation**: Document series are propagated from Purchase Orders to Vendor Bills and Stock Receipts, ensuring data consistency.
- **Validation**: Enforces that the selected Series matches the Document Type, preventing errors before submission to tax authorities.
- **Integration**: Works seamlessly across Purchase, Sales, and Inventory modules.

## Configuration
1.  **Define Document Types**:
    -   Go to **Accounting > Configuration > Document Types**.
    -   Ensure your required document types (e.g., '01' Factura, '03' Boleta) are created and active.

2.  **Configure Partner Defaults** (Optional):
    -   Go to **Contacts**.
    -   Open a Partner record.
    -   In the **Accounting** tab, set the default **Document Type** for this partner. This will override the general default when creating documents for this partner.

3.  **Journal Configuration**:
    -   Go to **Accounting > Configuration > Journals**.
    -   On Purchase or Sale journals, you can specify default behavior for document types if needed.

## Usage

### Purchase Workflow
1.  Create a **Purchase Order** for a vendor.
2.  Confirm the order.
3.  **Receipts**: The generated Stock Picking (Receipt) will automatically have the **Document Type** field filled based on the configuration. You just need to enter the **Series** and **Number** provided by the vendor.
4.  **Vendor Bills**: When creating a Bill from the PO, the **Document Type** is also pre-filled. Enter the document number (Series-Number), and the validation logic will ensure it matches the expected format.

### Stock Transfers
1.  Go to **Inventory > Operations > Transfers**.
2.  Create a new Transfer.
3.  Select a **Partner**. The **Document Type** field will update automatically if the partner has a specific default set.
4.  Enter the **Entity** and **Number** for the guide.

## Support
For support, please contact us at [leads@ganemo.com](mailto:leads@ganemo.com) or visit our website.
