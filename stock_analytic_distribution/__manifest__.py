{
    "name": "Stock Analytic Distribution",
    "version": "19.0.1.0.1",
    "category": "Inventory/Inventory",
    "summary": """Set an analytic distribution on transfers, stock moves and """
    """scraps, post it to the inventory valuation entries and analyze it.""",
    "description": """
Stock Analytic Distribution
===========================

Assign an analytic distribution to your transfers, stock moves and scraps.
When inventory is valued in real time, the distribution is posted on the
valuation journal entry the native Odoo way, so the analytic items are
generated and linked automatically. Set it once on the transfer header to
autocomplete every move, and filter or group your stock by analytic account.
""",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": [
        "stock_account",
        "analytic",
    ],
    "data": [
        "views/account_analytic_plan_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_move_views.xml",
        "views/stock_move_line_views.xml",
        "views/stock_scrap_views.xml",
    ],
    "icon": "/stock_analytic_distribution/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 110.0,
    "module_type": "official",
}
