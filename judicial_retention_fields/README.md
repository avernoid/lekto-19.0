# Judicial Retention Fields

<img src="static/description/banner.png" width="100%" alt="Banner">

**Author**: [Ganemo](https://www.ganemo.co/) | **License**: OPL-1 | **Odoo**: 19 Enterprise

## Overview

`judicial_retention_fields` adds a dedicated **Judicial Processes** section to the employee form (Personal Information tab) to manage judicial withholdings such as child support, alimony, or any court-mandated salary deduction. It provides all the data fields necessary for payroll salary rules to calculate and apply the retention, and generates an official **Judicial Retention PDF report** printable from payslips.

> ⚠️ Requires **Odoo 19 Enterprise**. Not compatible with Odoo Community or Odoo Online (SaaS).

---

## Key Features

- **Fixed & Percentage Retention** — Store either a fixed monetary amount (`judicial_discount`) or a percentage (`judicial_discount_percent`) for use by payroll salary rules.
- **Beneficiary Management** — Assign a specific contact (partner) as beneficiary, with relationship bond, identification type, and document number.
- **Filtered Bank Account** — The `account_number` selector is restricted to the beneficiary's registered bank accounts. Creating a new account pre-fills the beneficiary as the owner. Only "Create and Edit" is allowed (no quick create) to ensure data completeness.
- **Auto-fill Bank & CCI** — Bank name and Interbank Code (CCI) are computed automatically from the selected bank account.
- **Payment Type** — Select the disbursement method (bank transfer, check, cash) via the shared `payment.type` catalog. Bank fields are only visible when a bank transfer type is selected.
- **Validity Period** — Optional `start_date`/`end_date` for salary rules to enforce time-bound retentions.
- **Maximum Cap** — `retention_amount` field to set a cumulative cap for the retention.
- **Retention Base** — `retention_on` selection to specify which income basis (Total, Taxable, Non-Taxable, Net Income, Net Payable) the percentage applies to.
- **Settlement Retention Flag** — `settlement_retention` boolean to control whether the retention applies to termination/liquidation payslips.
- **Judicial Retention PDF Report** — Server action "Judicial R. Format" available from the Payslips list (Action menu). Generates an A4 PDF per payslip with beneficiary details, bank, account number, paid amount (from salary rule codes `DJF_001` / `DJP_002`), and signature slots.

---

## Employee Form Fields (Personal Information → Judicial Processes)

| Field | Type | Description |
|---|---|---|
| `judicial_discount` | Float | Fixed amount to deduct per payroll period |
| `judicial_discount_percent` | Float | Percentage of the salary base to deduct |
| `exists_beneficiary` | Boolean | Toggle that reveals all beneficiary fields |
| `beneficiary` | Many2one (res.partner) | Contact designated to receive the funds |
| `bond` | Char (10) | Relationship: Child, Spouse, etc. |
| `card_type_id` | Many2one (l10n_latam.identification.type) | Beneficiary ID document type |
| `card_id` | Char | Beneficiary identification number |
| `payment_type` | Many2one (payment.type) | Payment method for the disbursement |
| `account_number` | Many2one (res.partner.bank) | Beneficiary bank account (filtered by beneficiary) |
| `bank` | Char (computed) | Bank name — auto-filled from account_number |
| `cci` | Char (computed) | Interbank Code — auto-filled from account_number |
| `start_date` | Date | Retention valid from |
| `end_date` | Date | Retention valid to |
| `retention_amount` | Float | Maximum cumulative retention cap |
| `settlement_retention` | Boolean | Apply retention to settlement payslips |
| `retention_on` | Selection | Income base for percentage calculation |

All fields are restricted to `hr.group_hr_user` (HR Officer) and above.

---

## Configuration & Usage

1. Go to **Employees ▸ Employees** and open the employee record.
2. Navigate to **Personal Information** tab → **Judicial Processes** group.
3. Enter the **Judicial Discount** (fixed) or **Judicial Discount Percentage**.
4. Check **Exists Beneficiary?** to reveal beneficiary fields.
5. Select or create the **Beneficiary** (contact/partner).
6. Select the **Judicial Payment Type**. If bank transfer: select the **Account Number** (filtered to the beneficiary's accounts — use "Create and Edit" to add a new one; the partner is pre-filled).
7. Optionally set **Valid From / Valid To**, **Maximum Retention Amount**, **Retention Based On**, and **Retain from Settlement?**.

### Generating the Judicial Retention PDF

1. Go to **Payroll ▸ Payslips**, select one or more validated payslips.
2. Click **Action (⚙) ▸ Judicial R. Format**.
3. An A4 PDF is generated with: beneficiary name and document, bank and account number, currency (SOL), paid amount, and signature slots for Beneficiary and Notified (employee).

> **Note:** The PDF paid amount is the sum of payslip lines with codes `DJF_001` (fixed) and `DJP_002` (percentage). These codes must be used in your salary rules for the amount to appear correctly.

---

## Technical Dependencies

```
additional_fields_voucher
payment_conditions
type_bank_accounts
```

---

## Global Support

Translations included for **English** and **Spanish** (en_US, es_ES, es_PE, es_MX).

---

© 2026 [Ganemo](https://www.ganemo.com) — All rights reserved.
