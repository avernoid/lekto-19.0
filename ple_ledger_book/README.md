# **Accounting Ledger PLE - SUNAT (Perú)**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Overview

This module generates the **electronic General Ledger (Libro Mayor)** — **Registro 6.1** — required by SUNAT for Peruvian companies with complete accounting obligations.

It produces ready-to-upload `.txt` files compliant with both **PLE** and **SIRE** reporting formats, plus `.xlsx` Excel files for internal review and audit purposes. Reports are generated directly from Odoo with a single click.

## Features

- **Dual Format Support**: Automatically selects PLE format (periods before October 2023) or SIRE format (from October 2023 onwards) based on the report period
- **Ready-to-Upload TXT**: Files follow SUNAT's exact naming convention (`LE{RUC}{period}060100...`) and column structure
- **Excel Reports**: Detailed `.xlsx` spreadsheets with formatted headers and data for internal review
- **High-Performance SQL**: Uses optimized raw SQL queries for fast data extraction, processing thousands of records in seconds
- **State Management**: Built-in workflow with **Draft → Loaded → Declared** states to track reporting status
- **Rollback Support**: Return declared periods to draft to regenerate reports with updated data
- **Multi-Company**: Each report is linked to a specific company, filtering journal entries accordingly

## Dependencies

| Module | Purpose |
|---|---|
| `ple_sale_book` | Provides the base PLE report model (`ple.report.base`) and menu structure |
| `ple_purchase_book` | Provides the `is_nodomicilied` field on `account.move` |
| `invoice_type_document` | Propagates `serie_correlative` and `l10n_latam_document_type_id` to journal entries |

> All dependencies are installed automatically when you install this module.

## Configuration

No additional configuration is required beyond having the dependencies installed. The module uses the company's RUC (VAT number) and the Peruvian localization data (`l10n_pe`) that is part of the standard Odoo setup.

### Prerequisites

1. **Peruvian Localization**: Ensure `l10n_pe` (Peruvian Chart of Accounts) is installed and configured
2. **Company RUC**: The company must have a valid 11-digit RUC number set in the VAT field
3. **Posted Entries**: Only posted (`state = 'posted'`) journal entries are included in reports

## Usage

### Step 1: Create a Report Record

Navigate to **Accounting → PLE → Libros Mensuales → Libro Mayor**.

Click **Create** and fill in:
- **Company**: Select the company to report for
- **Start Date**: First day of the reporting period (e.g., `2024-01-01`)
- **End Date**: Last day of the reporting period (e.g., `2024-01-31`)

### Step 2: Generate the Report

Click **"Generar Reporte"**. The system will:
1. Execute a SQL query to extract all posted journal entries for the period
2. Format the data according to PLE or SIRE structure (based on the period)
3. Generate both TXT and Excel files
4. Display download links on the form

### Step 3: Review and Download

- Download the **Excel file** for internal review. It contains formatted columns with headers
- Download the **TXT file** for uploading to SUNAT's PLE application

### Step 4: Declare to SUNAT

When ready, click **"Declarar a SUNAT"** to mark the period as officially reported. The record moves to **Closed** state.

### Step 5: Rollback (Optional)

If you need to regenerate (e.g., corrections were made), click **"Regresar a Borrador"**. This clears the files and returns the record to Draft state.

## Report Columns (TXT)

The TXT file contains the following fields per SUNAT specification:

| # | Field | Description |
|---|---|---|
| 1 | Period | Reporting period (YYYYMM00) |
| 2 | CUO | Unique Operation Code (journal entry sequence) |
| 3 | Journal Correlative | Sequential number within the journal |
| 4 | Account Code | Account plan code |
| 5 | Unit Code | Business unit code |
| 6 | Analytic Account | Cost center code |
| 7 | Currency | ISO currency code |
| 8 | Partner Doc Type | Partner's document type (DNI, RUC, etc.) |
| 9 | Partner VAT | Partner's tax identification number |
| 10 | Invoice Doc Type | Document type code (Factura, Boleta, etc.) |
| 11 | Series | Document series |
| 12 | Correlative | Document correlative number |
| 13 | Date | Accounting date |
| 14 | Due Date | Payment due date |
| 15 | Invoice Date | Invoice issuance date |
| 16 | Gloss | Description/label of the journal item |
| 17 | Ref Gloss | Reference description |
| 18 | Debit | Debit amount (2 decimals) |
| 19 | Credit | Credit amount (2 decimals) |
| 20 | Structured Data | PLE or SIRE format data block |
| 21 | State | Record state indicator (1 = active) |

## Technical Notes

### Serie/Correlativo Logic

The module uses a **multi-source fallback** strategy for determining the Series and Correlative of each journal entry:

1. **Primary**: `serie_correlative` field (provided by `invoice_type_document`)
2. **Fallback 1**: `move.name` (Odoo's internal entry number)
3. **Fallback 2**: `move.ref` (external reference)

This logic is **complementary** to `invoice_type_document`'s propagation (which copies `serie_correlative` from invoices to related entries like payments). The Libro Mayor's fallback ensures entries without propagated data still produce valid output.

### PLE vs SIRE Format

The transition date is **September 30, 2023**:
- **Before**: PLE format (structured data based on journal type and domicile status)
- **After**: SIRE format (structured data including partner VAT, document type, series, and correlative)

### SQL Functions

The module installs 5 PostgreSQL functions:
- `get_data_structured_ledger()` — PLE-format structured data
- `get_data_structured_sire()` — SIRE-format structured data
- `get_journal_correlative()` — Journal correlative based on contributor type
- `string_ref()` — String sanitization (removes special characters)
- `UDF_numeric_char_ledger()` — Numeric formatting (2 decimal places)

## Compatibility

| Platform | Supported |
|---|---|
| Odoo Enterprise 19.0 | ✅ |
| Odoo.SH | ✅ |
| Ganemo Online / Ganemo.SH | ✅ |
| Odoo Online (SaaS) | ❌ (requires custom code) |

## Troubleshooting

### Empty TXT file
**Cause**: No posted journal entries exist for the selected period/company.
**Fix**: Verify entries are in **Posted** state. Draft entries are excluded.

### Wrong Serie/Correlativo
**Cause**: The `invoice_type_document` module may not be propagating correctly.
**Fix**: Check that source invoices have valid `serie_correlative` values.

### Menu not visible
**Cause**: Missing dependencies.
**Fix**: Ensure `ple_sale_book` is installed (provides the parent menu).

## Changelog

### 19.0.1.0.0
- Migrated to Odoo 19
- Updated `exchange_rate` to `invoice_currency_rate` in tests
- Updated license to OPL-1
- Added professional branding (icon, banner, index.html)

### 18.0.1.0.1
- Initial release for Odoo 18

---

**Author**: [Ganemo](https://www.ganemo.com)