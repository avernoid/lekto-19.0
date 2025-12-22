# Stock Delivery Payment Control

## Overview

**Stock Delivery Payment Control** is an essential module for businesses that need to enforce strict credit control policies at the point of delivery. It prevents the validation of outgoing shipments (delivery orders) if the associated sales order is not paid or if the partner does not meet the required credit terms.

This module helps you:
*   **Secure Revenue**: Ensure goods only leave your warehouse when payment terms are met.
*   **Automate Checks**: Eliminate manual communication between Warehouse and Accounting.
*   **Manage Splits**: Handle partial deliveries and backorders with intelligent value calculation.

## Features

*   **Payment Status Check**: Automatically calculates if a Sales Order is "Fully Covered", "Partially Covered", or "Not Covered" based on invoices and registered payments.
*   **Smart Validation**: Intercepts the `button_validate` action on Stock Pickings to block deliveries that violate the payment policy.
*   **Credit Term Analysis**: Respects payment terms (e.g., "30 Days"). If a customer has a valid credit term (`nb_days > 0`) that is not yet due, the delivery is allowed even if unpaid.
*   **Granular Configuration**:
    *   **Global Defaults**: Configure policy defaults on the Customer (`res.partner`) or Sales Team (`crm.team`).
    *   **Per-Order Override**: Manually adjust settings on specific Sales Orders.
    *   **Operation Type Control**: Define exactly which operation (e.g., "Pick", "Pack", or "Delivery") enforces the check, ensuring compatibility with multi-step routes.
*   **Detailed Feedback**: Provides clear, blocking error messages to the warehouse user explaining exactly why a transfer cannot be validated.

## Configuration

### 1. Operation Types (Critical)
To enable the control, you **must** activate it on the specific Operation Type (usually *Delivery Orders*):
1.  Go to **Inventory > Configuration > Operation Types**.
2.  Select your outgoing operation (e.g., `WH/OUT`).
3.  Check the box **"Enforce Payment Control"**.
    *   *Note: In multi-step routes (Pick + Pack + Ship), only enable this on the final 'Ship' step to avoid blocking internal transfers.*

### 2. Defaults (Optional)
You can set default policies for new orders:
*   **On Customer**: Go to the Contact form > Sales & Purchase tab.
*   **On Sales Team**: Go to CRM > Configuration > Sales Teams.

Available settings:
*   **Payment Control Active**: Enable/Disable the logic.
*   **Validation Level**:
    *   *Sale Order Level*: Requires the entire order to be paid/covered.
    *   *Picking Level*: checks if the *paid amount* covers the *cumulative delivered value* (including the current picking).
*   **Require Full Payment**: If enabled, partial payments are not enough; 100% payment is required.

## Usage

1.  Create a **Sales Order** and Confirm it.
2.  The `Payment Control Active` flag will key off your defaults.
3.  Go to the generated **Delivery**.
4.  If the order is unpaid (and no credit term exists):
    *   The `Payment Coverage` ribbon will show **"Not Covered"**.
    *   Clicking **Validate** will raise an error: *"Blocking Validation: Payment not covered"*.
5.  Register a Payment on the Sales Order (full or partial depending on config).
6.  Return to the Delivery. The ribbon will update to **"Fully Covered"** or **"Partially Covered"**.
7.  Click **Validate**. The transfer proceeds.

### Logic Matrix

| Status | Control Active? | Payment Covered? | Valid Credit Term? | Can Validate? |
| :--- | :---: | :---: | :---: | :---: |
| **No Control** | ❌ | N/A | N/A | ✅ Yes (Always) |
| **Not Covered** | ✅ | ❌ No | ❌ No | ⛔ **Blocked** |
| **Partially Covered** | ✅ | ⚠️ Partial | ❌ No | ⚠️ **Depends** (Blocked if *Require Full Payment* is ON) |
| **Fully Covered** | ✅ | ✅ Yes | N/A | ✅ Yes |
| **Credit Not Due** | ✅ | ❌/✅ Any | ✅ Yes (`nb_days > 0`) | ✅ Yes |

## Compatibility

*   **Odoo Version**: 19.0 (and 18.0 compatible)
*   **Multi-Company**: Yes, works with standard multi-company rules.
*   **Multi-Currency**: Yes, uses standard Odoo monetary comparisons.

## Credits

**Author**: [Ganemo](https://www.ganemo.com)
