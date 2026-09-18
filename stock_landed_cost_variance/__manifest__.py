{
    "name": "Stock Value Variance",
    "version": "19.0.2.0.0",
    "category": "Inventory",
    "summary": "Correct the cost of goods already gone when a landed cost, a bill or a credit note arrives late.",
    "description": """
When a landed cost, a vendor bill with another price or exchange rate, a
subcontractor bill or a customer credit note changes the cost of goods that
have already left, Odoo 19 corrects the product cost but never the stored
value of the deliveries -- and the accounting ends up split, with no cause
anyone can point at, between the freight account, inventory and cost of sales.

For every such event this module:

* rewrites the value of the affected deliveries to the cost Odoo's own
  valuation engine gives them today (average, FIFO, lots, consignment);
* records every amount with the date of the event, so reports rebuild any
  past date exactly as it was known then;
* posts one identified journal entry dated on the event, linked to the
  landed cost, bill or credit note that caused it;
* cascades the change to manufactured and subcontracted goods;
* books the value Odoo's average replay drops when goods arrive on negative
  stock.

It never blocks nor silently reverses a native operation: every event keeps
a status that shows whether its entry is posted, not needed or outdated.
    """,
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    "depends": ["stock_landed_costs", "purchase_stock", "sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/stock_value_variance_views.xml",
        "views/stock_value_revaluation_views.xml",
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
