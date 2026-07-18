# **Kardex PLE 13.1 - Transfer Document Bridge**

<img src="static/description/banner.png" width="100%" alt="Banner">

**Author**: [Ganemo](https://www.ganemo.com)

## Description

This is the **bridge** that lets the Peruvian **PLE 13.1** (*Registro de Inventario Permanente Valorizado* / Kardex) report use the fiscal document captured by **`invoice_type_document_extension`**.

The native Kardex derives each line's document type, series and folio from the invoice `name`, the remission guide, or a `00` fallback. This bridge overrides the report so that, **when a stock movement carries a captured transfer document type**, the report uses that document (type + series + number) instead — atomically, and only for movements you have actually populated.

## How it works

- The bridge re-implements the native `_get_ple_report_content` and injects the captured document **after** the native force-to-`09` and **before** the value scrub.
- The injection is **gated by the captured document type** (`transfer_document_type_id`). If a movement has no captured type, the bridge does nothing and the native behaviour stands — it can never turn a compliant `09`/invoice line into an illegal `00`.
- When present, the captured **type + series + number** replace the derived ones atomically (they always come from the same document).

## Safety

- **Zero effect until you populate data.** On install, every movement is empty, so the report is **byte-identical** to the native one. Only populating a movement's transfer document (via the capture module) changes that movement's PLE line — a deliberate action, not an install side effect.
- **Not auto-installed.** Install it only on the clients that want the Kardex to read the captured document.
- **Regression test that blocks bad deploys.** The bridge copies the native report method verbatim; a `post_install` test compares bridge-vs-native output on empty data **and** hashes the native source (fingerprint). If Odoo updates the native method, the fingerprint changes and the test fails hard — signalling that the copy must be re-synced before the PLE TXT can silently diverge from what SUNAT expects.

## Requirements & Compatibility

- Odoo **19** (Enterprise / Odoo.SH).
- `countries = ['pe']` — only applicable to Peruvian companies.
- Depends on: `l10n_pe_reports_stock` (the native Kardex) and `invoice_type_document_extension` (the capture).

## Installation

1. Install **`invoice_type_document_extension`** and this bridge.
2. Generate the PLE 13.1 report as usual (**Accounting ▸ Reporting ▸ Peru ▸ PLE Stock reports**). Movements you have populated will now report their captured document.

## Usage

There is no configuration screen. Populate the transfer document on your stock movements (automatically or manually, via `invoice_type_document_extension`) and generate the report — the captured values flow into the Kardex.

## Support

For commercial inquiries: [leads@ganemo.com](mailto:leads@ganemo.com).
For technical support and bug reports: [ayuda@ganemo.com](mailto:ayuda@ganemo.com) or visit [ganemo.co](https://www.ganemo.co).
