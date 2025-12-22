# Cashier Journal Control

## Overview

In multi-cashier environments, users often see all available journals in the payment wizard, leading to potential errors where a cashier might select the wrong cashbox. Additionally, manually selecting the correct journal for every transaction is time-consuming.

**Cashier Journal Control** solves these issues by allowing you to restrict which journals are visible to specific users. It also enables you to set a "Default Cash" journal per user, ensuring that the correct journal is pre-selected automatically. If no default is assigned, the system forces the user to make a conscious selection by leaving the field empty.

## Features

- **User-Specific Journal Assignment:** Assign specific users to journals to restrict visibility in the Payment Register wizard.
- **Default Cash Journal:** Mark a journal as "Default Cash" for assigned users.
- **Automatic Pre-selection:** The module automatically selects the user's default cash journal in payments.
- **Strict Control:** If no default journal is assigned, the journal field is left empty to ensure manual verification.
- **Multi-Company Support:** Fully compatible with multi-company environments.
- **Native Logic Extension:** Respects Odoo's native filtering (Bank/Cash/Credit types) while adding granular control.

## Configuration

1. Go to **Accounting > Configuration > Journals**.
2. Open a **Cash** or **Bank** journal form.
3. Navigate to the new **"Cashier Control"** tab.
4. **Allowed Users**: Add the users who should have access to this journal in the payment wizard. If left empty, the journal remains visible to all (subject to native rules).
5. **Default Cash**: Check this box if you want this journal to be auto-selected for the assigned users.

## Usage

1. Open a Customer Invoice or Vendor Bill.
2. Click on **"Register Payment"**.
3. The **"Journal"** field will behave as follows:
    - **Pre-selected:** If you have an assigned "Default Cash" journal.
    - **Empty:** If you do not have a "Default Cash" journal assigned (forcing manual selection).
    - **Hidden:** Journals not assigned to you (if restrictions are set) will not appear in the dropdown.

## Credits

**Author**: [Ganemo](https://www.ganemo.co)
