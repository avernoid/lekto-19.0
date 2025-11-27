# Sale One Step Invoice

## Overview
This module streamlines the invoicing process in Odoo by allowing Sales Teams to skip the standard "Create Invoice" wizard and optionally post the invoice automatically. This is ideal for businesses that always use the 'delivered' payment method and want to reduce clicks and automate validation.

## Features
- **Skip Invoice Wizard:** Configure specific Sales Teams to bypass the "Create Invoice" wizard.
- **Auto-Post Invoices:** Optionally configure Sales Teams to automatically validate (post) the created invoice.
- **Configurable per Team:** Settings are applied at the Sales Team level, allowing flexibility across different departments.

## Configuration
1. Go to **CRM** > **Configuration** > **Sales Teams**.
2. Select the Sales Team you want to configure.
3. In the **Invoicing Configuration** section:
    - Check **Skip Invoice Wizard** to bypass the wizard.
    - Check **Create Posted Invoice** to automatically validate the invoice (requires "Skip Invoice Wizard").

## Usage
1. Create a **Sales Order** assigned to a configured Sales Team.
2. Confirm the order.
3. Click the **Create Invoice** button.
    - If configured, the invoice will be created immediately without the wizard.
    - If configured, the invoice will be automatically posted.

## Credits
**Author:** Ganemo
**Website:** [https://www.ganemo.co](https://www.ganemo.co)

## License
This module is licensed under the Odoo Proprietary License v1.0 (OPL-1).
