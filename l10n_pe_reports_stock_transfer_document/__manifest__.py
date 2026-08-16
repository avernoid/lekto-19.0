{
    "name": "Peru - Stock Reports Transfer Document (PLE 13.1 bridge)",
    "version": "19.0.3.0.0",
    "countries": ["pe"],
    "summary": "Feed the captured transfer document (type/serie/number) and the "
               "per-move SUNAT operation type into the Peruvian Kardex PLE.",
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
    "data": [],
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
