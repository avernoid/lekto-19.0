{
    'name': 'Stock Valuation Avco Recalc',
    'version': '19.0.1.1.0',
    'category': 'Inventory',
    'summary': 'Recalculate Average Cost (AVCO) from a past date.',
    'description': """
This module allows authorized users to correct valuation errors caused by retroactive changes to stock moves.
It implements a "Waterfall" recalculation algorithm that:
1. Calculates the "Genesis" balance (Qty/Value) via SQL snapshot at a start date.
2. Re-processes all subsequent moves sequentially.
3. Updates `stock.move` value and unit price (Operational only).
4. Generates an Audit Log for traceability.

Key Features:
- "Recalculate Valuation" Server Action in Stock Move list view.
- Confirmation Wizard with editable initial balances (God Mode).
- Dedicated Audit Log model.
- No impact on historical Account Entries (Journal Entries are NOT touched).
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['stock_account'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_valuation_audit_views.xml',
        'wizards/valuation_recalc_wizard_views.xml',
        'views/stock_move_action.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 60.0,
    'module_type': 'official',
    'images': ['static/description/banner.png'],
    'icon': '/stock_valuation_avco_recalc/static/description/icon.png',
}
