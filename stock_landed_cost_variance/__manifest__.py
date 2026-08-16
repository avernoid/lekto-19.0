{
    "name": "Stock Value Variance",
    "version": "19.0.1.0.0",
    "category": "Inventory",
    "summary": "Identify the part of a later revaluation that belongs to goods already gone.",
    "description": """
When a landed cost or a vendor bill revalues a receipt **after** part of the
goods have left, Odoo 19 adds the whole amount to the move's value but
capitalises only the part still in stock -- and posts nothing at all when
nothing is left.  The remainder stays in an expense account, unidentified.

This module records that remainder per movement (``stock.value.variance``),
so it can be:

* reported as its own line in a valued stock ledger, and
* reclassified to the product's cost of sales by an explicit journal entry,
  traceable back to the variance rows that substantiate it.

It creates no stock moves and never rewrites a done move's value.
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": ["stock_landed_costs", "purchase_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_value_variance_views.xml",
        "views/product_category_views.xml",
    ],
    "icon": "/stock_landed_cost_variance/static/description/icon.png",
    "images": ["static/description/banner.png"],
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": False,
    "currency": "USD",
    "price": 129.0,
    "module_type": "official",
}
