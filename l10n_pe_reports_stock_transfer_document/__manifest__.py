{
    "name": "Peru - Stock Reports Transfer Document (PLE 13.1 bridge)",
    "version": "19.0.5.0.0",
    "countries": ["pe"],
    "summary": "Captured transfer document and per-move SUNAT operation type in "
               "the Peruvian Kardex PLE, plus the normative corrections of "
               "fields 5, 6, 7, 8 and 10 and an audit of the period.",
    "description": """
Bridge module for the Peruvian Kardex PLE report.  It owns the single verbatim
copy of the native ``_get_ple_report_content`` and injects, per stock movement,
two captured values -- each gated on its own presence, so a movement without a
capture falls through to the native behaviour unchanged:

1. **Transfer document** (type + serie + number), captured by
   ``invoice_type_document_extension`` (LATAM layer): used instead of deriving
   the document from the invoice name.  Gated on the captured *type*.

2. **SUNAT operation type** (Table 12), captured per movement by
   ``l10n_pe_stock_operation_type`` (Peru layer): overrides the picking-derived
   operation type, injected before the '09' document coupling so the coupling
   reads the overridden value.  Soft-guarded on the field's presence, so this
   module does NOT hard-depend on the operation-type capture: install it to
   activate the injection, otherwise the native operation type stands.

It also carries the normative corrections of the Kardex PLE (RS 108-2020,
structures 12.1 and 13.1), which live here because this module already owns the
verbatim copy of the native method:

3. **Field 5** (catalogue of the existence code) and **field 7** (the code
   itself) become configurable on the product: which field feeds the code
   (internal reference, barcode or UNSPSC) and which Table 13 catalogue is
   declared for it.  The native hardcoded '1' declares United Nations for a
   code that is usually the client's own.

4. **Field 8** is emitted only when field 9 carries a code, instead of a fixed
   '1' next to an empty field 9.

5. **Field 6** of the opening (A1) rows is taken from the product, like the
   movement rows, instead of the native forced '99'.

6. **Field 10** never exceeds the period of field 1, as the norm validates: an
   invoice dated after the period falls back to the movement date.

7. An **Audit** button on the emission wizard reports, without blocking and
   without writing anything, what SUNAT would reject or observe.

A regression test (native-source fingerprint + native-vs-bridge comparison)
fails the build if the native source drifts and the copy must be re-synced.
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "category": "Accounting/Localizations/Reporting",
    "license": "OPL-1",
    "depends": [
        "l10n_pe_reports_stock",
        "l10n_pe_reports_stock_landed_costs",
        "invoice_type_document_extension",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_views.xml",
        "wizard/ple_audit_views.xml",
    ],
    # Opt-in per client: NOT auto-installed even when both deps are present.
    # Install it manually on the clients that want the Kardex to read the
    # captured transfer document.  (Design doc 4 said auto_install; overridden
    # by explicit request so not every client gets it.)
    "auto_install": False,
    "installable": True,
    "application": False,
    "icon": "/l10n_pe_reports_stock_transfer_document/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "currency": "USD",
    "price": 59.0,
    "module_type": "official",
}
