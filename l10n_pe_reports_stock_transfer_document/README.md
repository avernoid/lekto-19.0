# **Kardex PLE 12.1 / 13.1 - Transfer Document Bridge and Normative Corrections**

<img src="static/description/banner.png" width="100%" alt="Banner">

**Author**: [Ganemo](https://www.ganemo.com)

## Description

This is the **bridge** that lets the Peruvian **PLE 13.1** (*Registro de Inventario Permanente Valorizado* / Kardex) report use the fiscal document captured by **`invoice_type_document_extension`**, and the home of the **normative corrections** of the Kardex PLE — it owns the verbatim copy of the native report method, so the corrections cost no second copy.

The native Kardex derives each line's document type, series and folio from the invoice `name`, the remission guide, or a `00` fallback. This bridge overrides the report so that, **when a stock movement carries a captured transfer document type**, the report uses that document (type + series + number) instead — atomically, and only for movements you have actually populated.

## How it works

- The bridge re-implements the native `_get_ple_report_content` and injects the captured document **after** the native force-to-`09` and **before** the value scrub.
- The injection is **gated by the captured document type** (`transfer_document_type_id`). If a movement has no captured type, the bridge does nothing and the native behaviour stands — it can never turn a compliant `09`/invoice line into an illegal `00`.
- When present, the captured **type + series + number** replace the derived ones atomically (they always come from the same document).

## Normative corrections (RS 108-2020, structures 12.1 and 13.1)

| Field | Native | Here |
|---|---|---|
| **5** Catalogue of the existence code | Hardcoded `1` (United Nations) next to an internal reference | Configured on the product (Table 13: `1`, `3`, `9`), proposed from the code source, default `9` |
| **7** Existence code | Always `default_code` | The product chooses the source: internal reference, barcode or UNSPSC. No silent fallback: an empty source leaves the field empty, and SUNAT rejects the file |
| **8** Catalogue of field 9 | Hardcoded `1` even with field 9 empty | Emitted only when field 9 carries a code |
| **6** Type of existence on the opening (A1) rows | Forced to `99`, ignoring the product | Read from the product, like the movement rows |
| **10** Document date | The invoice date, even when it falls after the period | Falls back to the movement date when the document is dated after the period, which the norm rejects |
| **10** Document date (provenance) | The **first document by id** of the order line, whatever its type and even unposted — so a return printed its credit note's number next to the *invoice's* date | The date of **the document the row actually reports**, when the capture agrees with what the derivation resolves; drafts are never used, because field 10 is the *issue* date and a draft has not been issued |
| **7** (scrub) | Native strips `_ - / '` | Strips `_ / *` and **keeps the hyphen**: codes like `IH-21114` reach the book intact (task 69361, with its own test since 19.0.4.0.1) |

An **Audit** button on the emission wizard reports, without blocking and without writing anything, what SUNAT would
reject (empty existence code, unit of measure without a Table 6 code) or observe (catalogue that does not match the
code, type of existence unset, goods without UNSPSC, movements without a transfer, documents dated outside the period).

Nothing is filled with a default on the user's behalf: a file that passes validation carrying the wrong code is worse
than a rejected one.

## Late revaluations: each period as it was filed

With **`stock_landed_cost_variance`** (19.0.2 or later) installed, a freight, a bill at another price or a
subcontractor bill that arrives after the goods moved is written into the stored value of the movements. Printed
natively, a period already filed would change when regenerated. With the engine present, the 13.1 prints:

| Row | Value |
|---|---|
| Movement of the period | Its stored value, minus the amounts of events dated after the period |
| Landed cost of a movement of the period | Printed only if the landed cost is dated inside the period |
| Late amount of an event of this period on a movement of an earlier period | Its own line, with the event date (26 landed cost, 99 other) |
| Opening (A1) | The value known at the end of the previous day |

Measured on the real TXT: a filed period regenerates identically, each opening is the previous closing, and the
closing is the value known at the end of the period (the same figure the 3.7 prints with
`l10n_pe_reports_lib_stock_variance`). A bill posted after the period changes the document the native report derives
for the receipt (fields 12 and 13): that is native and not a value.

Without the engine, nothing of this applies and the file is the native one.

## Safety

- **The only differences with native are the ones listed above.** On install, every movement is empty, so the captured-document injection is inert and only the normative corrections separate the file from the native one. Populating a movement's transfer document (via the capture module) changes that movement's PLE line — a deliberate action, not an install side effect.
- **Field 5 changes from `1` to `9` on install** for every product that keeps the default source. It is the correct value, and SUNAT does not require consistency with previously filed periods, but the accountant should know before noticing it.
- **Not auto-installed.** Install it only on the clients that want the Kardex to read the captured document.
- **Regression test that blocks bad deploys.** The bridge copies the native report method verbatim; a `post_install` test compares bridge-vs-native output on empty data — normalising only the two columns the corrections deliberately change, which have dedicated tests of their own — **and** hashes the native source (fingerprint). If Odoo updates the native method, the fingerprint changes and the test fails hard — signalling that the copy must be re-synced before the PLE TXT can silently diverge from what SUNAT expects.

## Requirements & Compatibility

- Odoo **19** (Enterprise / Odoo.SH).
- `countries = ['pe']` — only applicable to Peruvian companies.
- Depends on: `l10n_pe_reports_stock` (the native Kardex) and `invoice_type_document_extension` (the capture).

## Installation

1. Install **`invoice_type_document_extension`** and this bridge.
2. Generate the PLE 13.1 report as usual (**Accounting ▸ Reporting ▸ Peru ▸ PLE Stock reports**). Movements you have populated will now report their captured document.

## Usage

Populate the transfer document on your stock movements (automatically or manually, via
`invoice_type_document_extension`) and generate the report — the captured values flow into the Kardex.

The existence code configuration lives on the product, in the **PE** group of the *Accounting* tab, next to *Type of
existence*: which field feeds the code, which catalogue is declared for it, and a preview of what the PLE will carry.
Before emitting, the **Audit** button of the wizard lists what SUNAT would reject or observe for the chosen period.

## Support

For commercial inquiries: [leads@ganemo.com](mailto:leads@ganemo.com).
For technical support and bug reports: [ayuda@ganemo.com](mailto:ayuda@ganemo.com) or visit [ganemo.co](https://www.ganemo.co).
