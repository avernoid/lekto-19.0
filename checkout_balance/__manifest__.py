# -*- coding: utf-8 -*-
{
    'name': 'Checkout balance',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Creates the trial balance report that includes the income statement by nature and by function.',
    'description': """
Checkout Balance Report
=======================
Advanced Trial Balance report for Odoo 19.
Includes columns for Initial Balance, Period Movements, Final Balance, and Income Statement by Function and Nature.
    """,
    'category': 'Accounting',
    'module_type': 'official',
    'depends': ['account', 'account_reports'],
    'data': [
        'data/checkout_balance_report.xml',
        'views/account_group_views.xml'
    ],
    'icon': '/checkout_balance/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 30.00
}
