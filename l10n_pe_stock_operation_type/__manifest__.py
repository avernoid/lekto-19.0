{
    "name": "Peru SUNAT Operation Type",
    "version": "19.0.1.1.1",
    "category": "Accounting/Localizations",
    "countries": ["pe"],
    "summary": "Capture the SUNAT Table 12 operation type per stock movement, "
               "with heuristic autocompletion, manual-edit protection and a "
               "mass-assignment wizard, for the Peruvian Kardex PLE.",
    "description": """
Peru SUNAT Operation Type per Stock Move
========================================

Peru capture layer, symmetric to the LATAM document-type capture: it moves the
SUNAT Table 12 operation type from the picking (native l10n_pe_reports_stock,
one type per transfer) down to each stock.move -- the natural grain of the
Peruvian Kardex PLE line, and the only place that can classify picking-less
moves (inventory adjustments, scrap, MRP).

Key features
------------
* Independent stored field on stock.move (not a related mirror of the picking).
* Own heuristic autocompletion on validation (sale -> 01, purchase -> 02,
  production -> 19/27, scrap -> 13, inventory adjustment -> 28, otherwise the
  transfer direction), as a smart default that is overridable by hand.
* Manual-edit protection: a provenance flag so automatic inference never
  clobbers an accountant's classification.
* One mass-assignment wizard (SOURCE: auto / from the picking / a fixed value,
  x POLICY: only empty / overwrite auto keeping manual / overwrite all), with
  dynamic explanatory banners and a live preview count, launchable from a
  stock.move list or a stock.picking list.

The PLE injection lives in the separate bridge module
(l10n_pe_reports_stock_transfer_document), which reads this field with a soft
guard: when set it wins, otherwise the native behaviour stands.
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "l10n_pe",
        "stock_account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/l10n_pe_operation_type_assign_views.xml",
        "views/stock_move_views.xml",
    ],
    "demo": [
        "demo/l10n_pe_stock_operation_type_demo.xml",
    ],
    "icon": "/l10n_pe_stock_operation_type/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 89.0,
    "module_type": "official",
}
