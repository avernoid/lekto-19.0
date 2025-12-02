# Flexible Invoice Policy

## Overview

This module adds a permission-controlled toggle to sales orders that allows authorized users to invoice the full ordered quantity immediately, regardless of the product's invoice policy configuration. It provides a clean exception mechanism for delivery-based invoicing without requiring product configuration changes.

## Features

- **Permission-Based Control**: Only users with the "Allow Invoice Without Delivery" security group can enable the exception toggle
- **Automatic Tracking**: All changes are logged in the order's chatter with username and timestamp for complete audit trail
- **Auto-Cleanup**: Toggle automatically resets after invoice creation (configurable via system parameter)
- **Native Integration**: Uses Odoo's built-in invoice policy override mechanism for seamless compatibility
- **Module Compatibility**: Works perfectly with `auto_invoice_on_delivery` and `sale_one_step_invoice` modules

## Installation

1. Download or clone this module into your Odoo addons directory
2. Update the apps list: `Settings → Apps → Update Apps List`
3. Search for "Flexible Invoice Policy"
4. Click Install

## Configuration

### 1. Assign Permissions

Navigate to `Settings → Users & Companies → Users` and edit the users who should be able to create invoice exceptions:

1. Open the user form
2. Go to the "Access Rights" tab
3. Under the Sales category, enable the **"Allow Invoice Without Delivery"** permission
4. Save

> **Recommended**: Assign this permission only to Sales Managers or Finance Managers who understand the implications of bypassing delivery requirements.

### 2. (Optional) Configure Auto-Cleanup Behavior

By default, the toggle automatically resets after invoice creation. To change this:

1. Go to `Settings → Technical → Parameters → System Parameters`
2. Create or edit the parameter: `sale_flexible_invoice_policy.auto_cleanup_flag`
3. Set value to:
   - `True` (default): Toggle resets after invoicing
   - `False`: Toggle remains enabled after invoicing

## Usage

### Normal Workflow (Delivery Policy Respected)

1. Create a sales order with products that have "Delivered Quantities" invoice policy
2. Confirm the order
3. Deliver the products
4. Click "Create Invoice"
5. Invoice only delivered quantities (standard Odoo behavior)

### Exception Workflow (Invoice Without Delivery)

1. Create a sales order with products that have "Delivered Quantities" invoice policy
2. Confirm the order
3. **Enable the "Allow Invoice Without Delivery" toggle** in the order header (only visible to authorized users)
4. The change is automatically logged in the chatter
5. Click "Create Invoice"
6. Invoice the full ordered quantity immediately, regardless of delivery status
7. The toggle automatically resets (if auto-cleanup is enabled)

### Integration with Auto-Invoice Modules

If you're using `auto_invoice_on_delivery` or `sale_one_step_invoice`:

- **With auto_invoice_on_delivery**: Enable the toggle before validating the delivery → Full quantity is auto-invoiced
- **With sale_one_step_invoice**: Enable the toggle with teams configured for one-step invoicing → Full quantity is invoiced and posted automatically

## Use Cases

This module is perfect for scenarios like:

- **Urgent customer requests**: Customer needs invoice immediately for accounting/payment processing
- **Rush orders**: Need to invoice before delivery for special cases
- **Prepayment scenarios**: Invoice upfront while maintaining delivery-based policy for regular orders
- **Exception handling**: Handle one-off cases without changing product configurations globally

## Security & Compliance

- **Permission Control**: Only authorized users can enable exceptions
- **Audit Trail**: Every toggle change is logged with user and timestamp
- **Auto-Reset**: Prevents accidental reuse of exception flag
- **Traceability**: Complete history in chatter for compliance reviews

## Known Issues / Roadmap

- None currently identified

## Bug Tracker

Bugs are tracked on [GitHub Issues](https://github.com/Ganemo/sale_flexible_invoice_policy/issues).

In case of trouble, please check there if your issue has already been reported. If you spotted it first, help us smashing it by providing a detailed and welcomed feedback.

## Credits

### Contributors

* Ganemo <https://www.ganemo.co>

### Maintainer

This module is maintained by Ganemo.

To get support or provide feedback, please contact us at leads@ganemo.co or visit https://www.ganemo.co
