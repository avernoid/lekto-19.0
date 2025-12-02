# Auto Invoice on Delivery

This module extends the functionality of Stock Picking (Delivery Orders) to facilitate invoice creation directly from the picking view.

## Features

- **"Facturar" Button**: Adds a button to the delivery order to trigger the invoice creation flow (same as "Create Invoice" on the Sales Order).
- **Auto-Invoice on Validate**: Option to automatically trigger the invoice creation flow immediately after validating the delivery.

## Configuration

1. Go to **Inventory > Configuration > Operations Types**.
2. Select an operation type (e.g., "Delivery Orders").
3. Under the **Facturación** (Invoicing) group:
    - Check **Emitir Factura** to enable the feature.
    - Check **Al Validar** to automatically trigger invoicing upon validation.

## Usage

### Manual Invoicing
1. Open a Delivery Order linked to a Sales Order.
2. Ensure the operation type has "Emitir Factura" enabled.
3. Once the delivery is Done, click the **Facturar** button in the header.

### Automatic Invoicing
1. Ensure the operation type has both "Emitir Factura" and "Al Validar" enabled.
2. Open a Delivery Order linked to a Sales Order.
3. Click **Validate**.
4. The system will validate the stock moves and immediately trigger the invoice creation flow (e.g., opening the invoice wizard or the created invoice).

## Credits

### Authors
* Ganemo

### Maintainers
This module is maintained by Ganemo.
