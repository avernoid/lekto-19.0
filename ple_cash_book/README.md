# **PLE Cash & Bank Book**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Overview

This module generates the **electronic Cash & Bank Register** (Libro Caja y Bancos) in TXT format, ready to present to SUNAT via the **PLE electronic book program**. This is a mandatory e-book for companies that are required to keep complete accounting in Peru.

The module produces two reports:
- **TXT 1.1 — Cash Report**: Journal entries from cash-type accounts.
- **TXT 1.2 — Bank Report**: Journal entries from bank-type accounts, including SUNAT bank codes and payment methods.

Both reports generate companion Excel files for internal review.

---

## Features

- **SUNAT-Compliant TXT Output**: Pipe-delimited format per SUNAT PLE specifications.
- **Dual Report Generation**: Cash (1.1) and Bank (1.2) in a single operation.
- **Excel Companion Files**: For internal audit and review.
- **Secure Parameterized SQL**: All queries use `%s` parameters — no SQL injection risk.
- **Multi-Company Support**: Filters by `company_root_id` using Odoo's JSONB account codes.
- **Report Lifecycle Management**: Draft → Load → Closed → Rollback states.
- **Payment Method Tracking**: Extends payment registration with SUNAT payment method (Medio de Pago).
- **Bank Entity Linking**: Links chart of accounts entries to Peruvian banks with SUNAT codes.

---

## Dependencies

| Module | Purpose |
|---|---|
| `ple_purchase_book` | Base PLE infrastructure (report model, utilities) |
| `invoice_type_document` | LATAM document type handling |
| `l10n_pe` *(indirect)* | Peruvian bank catalog with SUNAT codes (`l10n_pe_edi_code`) |

---

## Configuration

### 1. Bank Assignment on Accounts

1. Go to **Accounting > Configuration > Chart of Accounts**.
2. For each **Cash** or **Bank** account (account type = `asset_cash`), open the form.
3. Set the **Bank** field to the corresponding Peruvian bank entity.
4. The bank's SUNAT code (`l10n_pe_edi_code`) will be automatically used in the TXT 1.2 report.

### 2. Payment Method (Medio de Pago)

When registering payments for invoices:
1. If the journal is **Bank** type, the **Payment Method** (Medio de Pago) field appears.
2. Select the appropriate SUNAT payment method from the catalog.
3. This value is written to the TXT report as the payment means code.

> **Note**: For Cash journals, the Payment Method field is hidden (defaults to `003`).

---

## Usage

### Generating Reports

1. Navigate to **Accounting > PLE > Libro Caja y Bancos**.
2. Click **Create**.
3. Set the **Start Date** and **End Date** for the reporting period.
4. Click **Generar Reporte** to execute the queries.
5. Download the generated files:
   - **Efectivo (Cash)**: TXT and Excel files
   - **Cuentas Corrientes (Bank)**: TXT and Excel files

### Report States

| State | Description | Actions Available |
|---|---|---|
| **Draft** | Initial state, ready to generate | Generate Report |
| **Load** | Report generated, files ready | Declare to SUNAT, Rollback |
| **Closed** | Declared to SUNAT | Rollback |

- **Declarar a SUNAT**: Marks the report as officially submitted.
- **Regresar a Borrador**: Returns the report to draft state for re-generation.

---

## SQL Functions

This module installs PostgreSQL functions to support report generation:

| Function | Purpose |
|---|---|
| `data_structured_cash` | Structures cash/bank data for TXT output |
| `find_full_reconcile` | Identifies fully reconciled entries |
| `get_unit_operation_code` | Determines the SUNAT operation code |
| `UDF_numeric_char` | Formats numeric values as fixed-width character strings |

---

## Technical Details

### Models

| Model | Type | Description |
|---|---|---|
| `ple.report.cash.bank` | New | Main report model with state machine and file generation |
| `account.account` | Extended | Adds `bank_id` (Many2one to `res.bank`) |
| `account.payment` | Extended | Adds `means_payment_id` (Many2one to `payment.methods`) |
| `account.payment.register` | Extended | Adds `means_payment_id` and computed `inv` visibility field |

### Security

- Access restricted to **Accounting > Invoicing** group (`account.group_account_user`).
- Full CRUD permissions on `ple.report.cash.bank`.

### Odoo 19 Compatibility

- Uses `@api.depends` computed fields (no deprecated `@api.onchange`).
- Views use `<list>` tag (not deprecated `<tree>`).
- Inline `invisible="expression"` syntax (no `attrs` or `modifiers`).

---

## Troubleshooting

### Bank code is empty in TXT file
The bank entity linked to the account may not have a SUNAT code. Check **Contacts > Configuration > Banks** and verify `l10n_pe_edi_code` is populated. The `l10n_pe` module should have loaded this automatically.

### Report generates empty files
No journal entries exist for the selected date range in cash/bank accounts. Verify posted entries exist within the period and the correct company is selected.

### SQL error when generating report
A stored SQL function may not be loaded. Run `odoo-bin -u ple_cash_book` to reload them.

---

## Compatibility

- **Odoo Version**: 19.0
- **Editions**: Enterprise (Odoo.SH, Ganemo Online)
- **Localization**: Peru (`l10n_pe`)
- **Languages**: English, Spanish

---

**Author**: [Ganemo](https://www.ganemo.com)
