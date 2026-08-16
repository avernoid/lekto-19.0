{
    "name": "Stock Value Variance - Kardex Columns",
    "version": "19.0.1.0.0",
    "category": "Inventory",
    "summary": "Feed recorded value variances into the movement-level Kardex columns.",
    "description": """
Bridge module.  ``stock_move_kardex_qty`` owns the Kardex columns and depends on
``stock_account`` alone; ``stock.value.variance`` lives in a module that needs
``stock_landed_costs``.  Rather than forcing that dependency on every install of
the columns, the columns read a hook that returns nothing by default and this
bridge -- installed automatically when both sides are present -- supplies the
real source and declares the dependencies that keep the columns fresh.

Without it, the Kardex columns behave exactly as they did before.
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": ["stock_move_kardex_qty", "stock_landed_cost_variance"],
    "data": ["views/stock_move_views.xml"],
    "icon": "/stock_landed_cost_variance_kardex/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": True,
    "application": False,
    "currency": "USD",
    "price": 39.0,
    "module_type": "official",
}
