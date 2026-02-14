# **Electronic Journal Perú (PLE Libro Diario)**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Overview

This module generates the **Electronic Journal (Libro Diario Electrónico)** required by SUNAT for Peruvian companies that must keep complete accounting records. It produces TXT files (PLE Books 5.1, 5.2, 5.3, 5.4) and a comprehensive Excel report, all formatted and named according to SUNAT's specifications and ready to upload directly through the PLE application.

## Features

- **PLE TXT 5.1 — Journal**: Main electronic journal with all posted journal entries, debit/credit amounts, account codes, partner data, document types, and structured data.
- **PLE TXT 5.2 — Simplified Journal**: Simplified version for RER contributors.
- **PLE TXT 5.3 — Chart of Accounts (with values)**: Lists all accounts with codes, names, groups, and chart prefix per Table 17.
- **PLE TXT 5.4 — Chart of Accounts (without values)**: Account structure for reference.
- **Excel Report**: Full spreadsheet for internal review and audit.
- **SIRE Compatibility**: Automatically handles pre-SIRE (before Oct 2023) and post-SIRE structured data formats.
- **SUNAT File Naming**: Generated files follow SUNAT's naming convention (`LE` + RUC + Period + Book Code + Flags).
- **VAT Validation**: Prevents report generation if the company's RUC/VAT is not configured.

## Dependencies

| Module | Purpose |
|--------|---------|
| `ple_sale_book` | Base PLE report model, core SQL functions, and report lifecycle |
| `invoice_type_document` | Series and correlative number propagation to journal entries |
| `ple_purchase_book` | Complementary purchase data fields |

## Configuration

### 1. Company Setup
1. Go to **Settings → Companies** and select your company.
2. Ensure the **NIF/RUC** field is filled with your 11-digit RUC.
3. Set the **Code Prefix** to match SUNAT's Table 17 for your Chart of Accounts classification (used in PLE 5.3 and 5.4).
4. Configure the **PLE Contributor Type** field to indicate your company's contributor category.

### 2. Account Setup
- Each `account.account` record should have the **PLE Date Account** field set to the date the account was first used.
- The **PLE State Account** field should be set to indicate the account's current state in the chart.

## Usage

### Generating the Electronic Journal

1. Navigate to **Accounting → PLE Reports → Electronic Journal**.
2. Click **Create** to start a new report.
3. Select the **date range** (start and end dates for the reporting month).
4. Ensure the correct **Company** is selected.
5. Click **"Generar"** to execute the report.
6. **Download** the generated TXT and Excel files directly from the form view.
7. **Upload** the TXT file to SUNAT's PLE application — no renaming needed.

### Rollback & Regenerate

- Click **"Rollback"** (Reestablecer) to clear all generated files and return the report to draft state.
- Then click **"Generar"** again to produce updated reports with the latest posted data.

### Report Lifecycle

| State | Description |
|-------|-------------|
| **Draft** | Initial state. Ready to generate files. |
| **Load** | Files have been generated and are ready for download. |
| **Closed** | Report has been finalized. Use Rollback to return to Draft. |

## Technical Notes

### SIRE Date Threshold
- **Before October 2023**: Uses `get_data_structured_diary()` SQL function for structured data formatting.
- **After October 2023**: Uses Python-based construction with partner VAT, document type, series, and correlative.

### SQL Functions
The module installs several PostgreSQL UDFs:
- `get_data_structured_diary()` — Formats structured data for pre-SIRE periods.
- `get_data_structured_sire()` — Available but post-SIRE data is constructed in Python for optimization.
- `get_journal_correlative()` — Generates journal entry correlatives based on contributor type.
- `string_ref()` — String reference utility.
- `UDF_numeric_char_diary` — Numeric character formatting.

### Analytic Distribution
If journal entry lines have analytic distribution, the report includes the analytic account names as a comma-separated list in the corresponding column.

## Compatibility

| Environment | Supported |
|-------------|-----------|
| Odoo Enterprise (Odoo.SH) | ✅ |
| Ganemo Online / Ganemo.SH | ✅ |
| Odoo Online | ❌ (custom code restrictions) |

**Odoo Version**: 19.0

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Empty report / no data | Ensure journal entries are **Posted** for the selected period |
| VAT validation error | Go to Settings → Companies → fill the NIF/RUC field |
| Missing Chart prefix in 5.3/5.4 | Configure the Code Prefix on Company settings |
| SQL error on generation | Check the error message; common cause is missing SQL functions (reinstall module) |

## License

OPL-1 (Odoo Proprietary License v1.0)

**Author**: [Ganemo](https://www.ganemo.co)
