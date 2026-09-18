{
    'name': 'Stock Valuation Avco Recalc',
    'version': '19.0.3.0.0',
    'category': 'Inventory',
    'summary': 'Rebuild the stored value of historical stock movements with the late revaluation engine.',
    'description': """
Rebuilds the stored value of deliveries and customer returns of the selected products with the
same engine that handles late revaluations (stock_landed_cost_variance): the cost Odoo's own
valuation gives each exit, in (date, id) order.

For history the engine never saw -- movements done before it was installed -- or values damaged
by hand.  Every amount is recorded as a dated row, so periods before the chosen date keep the
values they were reported with.  No journal entry is posted, the product cost is refreshed by
Odoo itself, and manual valuations are kept.  Each run leaves an audit with the value before and
after of every movement.

Version 19.0.3 retires the adjustment and restatement modes, the waterfall algorithm, the SQL
write of the product cost and the deletion of valuation anchors.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['stock_account', 'stock_landed_cost_variance'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/stock_valuation_audit_views.xml',
        'wizards/valuation_recalc_wizard_views.xml',
        'views/stock_move_action.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 299.0,
    
    'images': ['static/description/banner.png'],
    'icon': '/stock_valuation_avco_recalc/static/description/icon.png',
}
