{
    "name": "Peru - PLE 3.7 with Late Revaluations",
    "version": "19.0.1.0.0",
    "countries": ["pe"],
    "category": "Accounting/Localizations/Reporting",
    "summary": "PLE 3.7 (inventory detail of account 20) printed with the value known at the end "
               "of the period, consistent with the PLE 13.1 and the stock valuation account.",
    "description": """
Bridge module between the Peruvian book 3.7 (``l10n_pe_reports_lib``) and the late
revaluation engine (``stock_landed_cost_variance``).  Installed automatically when both
are present.

The native 3.7 adds up the stored value of the stock movements.  Since late
revaluations are written into those stored values, a 3.7 regenerated for a past date
would carry freights and bills that arrived later.  This module prints, per product, the
value known at the end of the period -- the same figure that closes the PLE 13.1 of that
period.

It also takes the balance at the end of the last day of the period: the native query
compares the movement date with the date alone and leaves that day out.
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "license": "OPL-1",
    "depends": ["l10n_pe_reports_lib", "stock_landed_cost_variance"],
    "data": [],
    "auto_install": True,
    "installable": True,
    "application": False,
    "icon": "/l10n_pe_reports_lib_stock_variance/static/description/icon.png",
    "currency": "USD",
    "price": 0.0,
    "module_type": "official",
}
