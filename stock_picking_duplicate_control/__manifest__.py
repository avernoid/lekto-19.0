{
    'name': 'Stock Picking Duplicate Control',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Control duplicate lines in stock pickings with configurable policies.',
    'description': """
        This module adds a mechanism to control duplicate product lines in stock pickings.
        It allows configuring a policy (Allow, Warning, Block) on the picking type.
        - Checks for duplicate (Product, Description) pairs.
        - Shows a warning banner or blocks saving based on the policy.
        - validaton on-the-fly in stock moves.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['stock'],
    'data': [
        'views/stock_picking_views.xml',
        'views/stock_picking_type_views.xml',
    ],
    'icon': '/stock_picking_duplicate_control/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 49.0,
    'module_type': 'official',
}
