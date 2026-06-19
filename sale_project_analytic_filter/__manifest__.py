{
    "name": "Sale Project Analytic Filter",
    "version": "19.0.1.0.1",
    "category": "Accounting/Accounting",
    "summary": """Keep the analytic distribution off the stock valuation line """
    """of the COGS entry, so the two COGS lines do not cancel out.""",
    "description": """
Sale Project Analytic Filter
============================

When a project is created from a sales order, ``sale_project`` stamps the
project's analytic distribution on every invoice line that is not a
receivable/payable account. That filter is too coarse: it also tags the
COGS line booked on the product's *stock valuation* account, which is the
inventory counterpart of the Cost of Goods Sold pair. As a result the two
COGS lines carry the same distribution with opposite balances and cancel
each other out in the project's analytic ledger.

This bridge module reimposes the invariant that the stock valuation line
(the inventory counterpart) never carries analytic, while its counterpart
-- the COGS expense line -- does. After the standard computation runs, any
COGS line booked on the product's stock valuation account has its analytic
distribution cleared. This is the same criterion the inventory valuation
entry uses, so the behaviour is consistent across the suite.

The correction is self-neutralizing: if Odoo ever fixes the upstream
behaviour, there is simply nothing to clear and the module becomes a
harmless no-op. A per-company setting allows turning it off.
""",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "sale_project",
        "stock_account",
    ],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "icon": "/sale_project_analytic_filter/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 49.0,
    "module_type": "official",
}
