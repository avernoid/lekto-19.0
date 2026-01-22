{
    'name': 'Stock Picking Extras',
    'version': '19.0.1.0.1',
    'category': 'Inventory',
    'summary': """Instant logistical information for Stock Transfers: Package and Bundle counts.""",
    'description': """
        This module extends Odoo Stock Pickings to provide essential logistical data without altering stock flows.
        
        Key Features:
        - Packages Count: Uses Odoo's native package count.
        - Total Bundles: Logistics unit count (Packages + Loose Items).
        - Read-only fields in Form and List views.
        - Passive logic: Does not affect reservations or accounting.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['stock'],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'icon': '/stock_picking_extras/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 30.0,
    'module_type': 'official',
}
