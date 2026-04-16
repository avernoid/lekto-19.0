{
    'name': 'Account analytic default location',
    'version': '19.0.1.0.3',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'It allows establishing analytical accounts by default by a warehouse.',
    'description': """
This module extends the Odoo Analytic Distribution Models to support warehouse-specific criteria.
It adds three new key criteria to the distribution rules:
- Origin Warehouse
- Origin Location
- Destination Location

This ensures precise analytic tracking for inventory movements in multi-warehouse environments, automatically assigning the correct analytic account based on the physical flow of goods.
    """,
    'category': 'Accounting',
    'depends': ['stock_account', 'sale_stock', 'purchase_stock'],
    'data': ['views/account_views.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 50.00,
    'module_type': 'official',
    'icon': '/account_analytic_default_location/static/description/icon.png',
    'images': ['static/description/banner.png'],
}
