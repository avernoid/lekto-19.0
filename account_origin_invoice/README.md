**Origin of Rectified Documents**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Description
This module adds a section to customer corrective invoices (Credit Notes) containing fields that store the related Customer invoice information. It also adds the logic for these fields to auto-complete when using the "Add Credit Note" wizard. This ensures traceability and compliance with localizations requiring explicit reference to origin documents.

## Configuration
No special configuration is required. Install the module and it works out of the box with standard Odoo Invoicing.

## Usage
1. Go to an existing **Customer Invoice**.
2. Click on **Add Credit Note**.
3. Fill in the reason and date in the wizard and click **Reverse**.
4. The system automatically populates the origin invoice reference.
5. Open the newly created Credit Note. You will see the **Origin Document** section with the link to the original invoice.

**Author**: [Ganemo](https://www.ganemo.com)