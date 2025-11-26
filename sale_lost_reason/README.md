# Sale Lost Reason

## Overview

This module extends Odoo's Sales functionality by adding lost reason management for sales orders, similar to the CRM module's lost reason feature. It allows businesses to track and analyze why sales opportunities are lost, providing valuable insights for sales improvement.

## Features

- **Lost Reason Management**: Define and manage custom lost reasons for sales orders.
- **Team-Level Configuration**: Enable/disable lost reason requirement per Sales Team.
- **Wizard Interface**: User-friendly popup for selecting lost reasons when canceling orders.
- **Conditional Requirement**: Lost reason is only required when configured at the team level.
- **Sales Analytics**: Lost reasons are stored on orders for reporting and trend analysis.

## Configuration

1. Navigate to **Sales > Configuration > Sales Teams**.
2. Select or create a Sales Team.
3. Enable the **"Use Lost Reason"** checkbox in the team settings.
4. Navigate to **Sales > Configuration > Lost Reasons**.
5. Create and manage your lost reason options (e.g., "Price too high", "Competitor chosen", "No budget").

## Usage

When a sales order is canceled:

1. If the Sales Team has "Use Lost Reason" enabled.
2. A wizard will appear requiring the selection of a lost reason.
3. The order can only be canceled after selecting a reason.
4. The lost reason is stored on the order for future analysis.

## Use Cases

- **Sales Performance Analysis**: Identify common reasons for lost sales.
- **Competitive Intelligence**: Track how often competitors win deals.
- **Pricing Strategy**: Understand if pricing is a frequent blocker.
- **Process Improvement**: Identify bottlenecks in the sales process.

## Technical Details

### Dependencies

- `sale_management`

### Models

- `sale.lost.reason`: New model to define lost reasons.
- `sale.order`: Extended with `lost_reason_id` field.
- `crm.team`: Extended with `use_lost_reason` boolean field.

### Wizards

- `sale.lost.reason.wizard`: Transient model for capturing lost reasons during order cancellation.

## Credits

### Authors

- Ganemo

### Maintainer

This module is maintained by Ganemo.

For support and more information, please visit [https://www.ganemo.co](https://www.ganemo.co)
