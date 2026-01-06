{
    'name': 'Add reconcile date',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Add Reconciliation Date Field',
    'description': """
This module creates the “Reconciliation Date” field, meaning that when we reconcile records, the date on which they were reconciled will be entered.
When we reconcile records, Odoo will give you a complete reconciliation number with which when we go to our complete reconciliations we can identify them and see the records that were made on that date.
    """,
    'category': 'Accounting',
    'depends': ['account'],
    'data': ['views/account_full_reconcile_views.xml'],
    'icon': '/add_reconcile_date/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'currency': 'USD',
    'price': 30.00,
    'module_type': 'official'
}
