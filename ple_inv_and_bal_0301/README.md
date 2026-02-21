# **PLE 3.1 Balance Sheet – Statement of Financial Position**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Overview

This module generates the **PLE Format 3.1** (Estado de Situación Financiera) for Peru's SUNAT electronic reporting system. It produces compliant **Excel**, **TXT**, and **PDF** reports from your Odoo accounting data, mapping journal entries to the official EEFF (Estados Financieros) rubro hierarchy.

## Features

- **Multi-Format Output**: Generates Excel (.xlsx), TXT (.txt), and PDF reports simultaneously
- **4-Level EEFF Hierarchy**: Full rubro breakdown with Level 4 sub-detail visible in PDF output
- **Automatic Initial Balances**: Calculates opening balances for each EEFF rubro based on posted moves
- **Configurable Account Mapping**: Map your chart of accounts to EEFF rubros via a dedicated configuration screen and wizard
- **Multi-Company Isolation**: Record rules ensure users only see reports from their active company
- **Smart Defaults**: Period auto-defaults to previous year (Jan 1 – Dec 31); date_end auto-updates when date_start changes
- **Date Validation**: SQL constraint prevents date_end from being before date_start
- **Search & Filters**: Quick filters by state (Draft/Generated/Declared), group-by company, state, or period

## Dependencies

| Module | Purpose |
|--------|---------|
| `ple_sale_book` | Base PLE report infrastructure |
| `l10n_pe_catalog` | Peru SUNAT catalog selections |
| `ple_cash_book` | Shared PLE utilities |

## Installation

1. Place the module in your Odoo addons directory
2. Update the module list: **Settings > Activate Developer Mode > Apps > Update Apps List**
3. Search for "PLE 3.1" and click **Install**

## Configuration

### EEFF Account Mapping

Before generating reports, you must map your chart of accounts to the EEFF rubros:

1. Go to **Accounting > PLE Inv. y Bal. > Configuración EEFF**
2. Each rubro (e.g., "Activos Corrientes", "Pasivos No Corrientes") has a list of mapped accounts
3. Click on a rubro to see its mapped accounts and modify them as needed
4. Alternatively, use the **Update EEFF Wizard** to batch-assign accounts to rubros

### Account Form View

You can also configure EEFF mapping directly from each account:
- Go to **Accounting > Configuration > Chart of Accounts**
- Open any account and look for the EEFF-related fields

## Usage

### Generating a Report

1. Navigate to **Accounting > PLE Inv. y Bal. > 3.1 Estado de Situación Financiera**
2. Click **New**
3. The period defaults to the previous full year (Jan 1 – Dec 31)
4. Select the appropriate values for:
   - **Estado de Envío**: Defaults to "Empresa o Entidad Operativa"
   - **Catálogo EEFF**: Defaults to "OTROS NO CONSIDERADOS EN LOS ANTERIORES"
   - **Oportunidad de Presentación**: Defaults to "Al 31 de diciembre"
5. Click **Generar Reporte** to create the Excel, TXT, and PDF files
6. Download the generated files from the **Reportes** section on the right side of the form
7. Once reviewed, click **Declarar a SUNAT** to mark as declared

### Understanding the PDF Report

The PDF report shows a two-table layout:
- **Table 1**: Activo (Assets) with columns for Rubro, Saldo Contable, and Diferencia
- **Table 2**: Pasivo y Patrimonio (Liabilities & Equity) with the same columns
- Level 3 rows show subtotals in bold
- Level 4 rows appear indented below their parent Level 3 rubro with a lighter font

### Date Behavior

- Changing **Fecha Inicio** automatically updates **Fecha Fin** to December 31 of the same year
- A validation constraint prevents setting Fecha Fin before Fecha Inicio

## Multi-Company

Each company generates independent reports. When you switch companies using the top-bar selector, only that company's reports are visible. This is enforced via Odoo record rules at the database level.

## Technical Notes

### Models

| Model | Description |
|-------|-------------|
| `ple.report.inv.bal` | Main report model (inherits `ple.report.base`) |
| `eeff.ple` | EEFF rubro definitions (hierarchy of financial statement categories) |
| `ple.eeff.account.config` | EEFF-account mapping configuration |
| `ple.report.inv.bal.initial.balances` | Initial balance lines for each rubro |

### Generated Files

| File Type | Format | Purpose |
|-----------|--------|---------|
| Excel (.xlsx) | Detailed worksheet | Analysis and review |
| TXT (.txt) | Pipe-delimited | SUNAT PLE upload |
| PDF (.pdf) | Formatted report | Formal presentation with Level 4 detail |

## Compatibility

- **Odoo Version**: 19.0
- **Editions**: Enterprise (Odoo.SH, Ganemo Online, Ganemo.SH)
- **Languages**: English, Spanish (es_ES, es_PE, es_MX)

## License

OPL-1 (Odoo Proprietary License v1.0)

**Author**: [Ganemo](https://www.ganemo.co)