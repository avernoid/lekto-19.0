# Force Exchange Rate

<img src="static/description/banner.png" width="100%" alt="Banner">

## Overview

**Force Exchange Rate** empowers accounting teams to manually override the system's default currency conversion rates on specific transactions. Whether you need to apply a negotiated spot rate, a specific tax authority rate (e.g., Detractions), or correct a historic entry, this module ensures your Journal Entries reflect exactly the value you define.

## Features

- **Wizard Integration**: Seamlessly force the rate directly from the "Register Payment" wizard on Invoices.
- **Auto-Logic for "Detracciones"**: Automatically retrieves historical rates (Invoice Date) when using a Payment Method named "Detracción".
- **Smart Auto-Complete**: Manual payments suggest the daily rate but allow instant overriding.
- **Entry Safeguard**: Journal Entries created from forced payments inherit the rate automatically. Manual entries pre-fill with market rate instead of 0.00.
- **Precedence Logic**: Forced rates strictly override date-based rates.

## Configuration

No complex configuration is required.
1. Install the module.
2. Ensure **Multi-Currency** is active in **Settings > Accounting**.
3. **Important:** If you want to use the automatic historical rate feature for Tax/Detractions, create a **Payment Method** named exactly `Detracción`.

## Usage Guide

### 1. Forcing Rate via Payment Wizard
When registering a payment:
1. Open the Invoice.
2. Click **Register Payment**.
3. **Normal Case**: The field **Forzar T.C.** defaults to the invoice rate. You can edit it.
4. **Detracción Case**: If you select the Payment Method `Detracción`, it will **automatically** look up the Exchange Rate of the Invoice Date and lock it in.

### 2. Manual Payments
1. Go to **Accounting > Vendor > Payments**.
2. Click **New**.
3. Select a Foreign Currency.
4. The **Forzar T.C.** field automatically fills with today's system rate.
   - *Action*: If you change the **Date**, the rate updates automatically.
   - *Override*: Type a new rate (e.g., 4.10) to lock it in.
5. Confirm the payment.

### 3. Manual Journal Entries
1. Go to **Accounting > Accounting > Journal Entries**.
2. Create a new Entry in a Foreign Currency.
3. The **Invoice Currency Rate** field will pre-fill with the Market Rate (instead of 0.00).
4. Editing this rate will recalculate the debit/credit amounts for the lines.
   - *Note*: If the Entry comes from a Payment with a Forced Rate, this field is read-only or pre-filled with the forced value.

## FAQ & Troubleshooting

**Q: Why does the rate field show 0.00 on some old entries?**
A: 0.00 indicates that the system used the default daily rate table. This module only displays a value if a specific rate is being forced or suggested.

**Q: Which rate wins: The Date or my Manual Input?**
A: Your Manual Input (Forced Rate) always takes priority. If you clear the field (set to 0.00), the system falls back to the Date-based rate.

**Q: Does this affect standard Invoices?**
A: No. Standard invoices continue to use Odoo's native logic. This module specifically targets Payments and Adjustments where the rate often differs from the invoice date.

## Credits

**Author**: [Ganemo](https://www.ganemo.co)