{
    'name': 'Cashier Journal Control',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Payment',
    'summary': 'Control which journals are available and default in payment register wizard.',
    'description': """
        This module allows controlling which journals are visible and selected by default 
        in the Payment Register wizard (account.payment.register).
        
        Features:
        - Assign users to specific journals (Cash/Bank).
        - Mark a journal as "default cash" for its assigned users.
        - In the payment wizard, only "allowed" journals are shown.
        - The default journal is auto-selected based on the "default cash" flag and user assignment.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'icon': '/cashier_journal_control/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'depends': ['account'],
    'data': [
        'views/account_journal_views.xml',
        'views/account_payment_register_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 75.0,
    'module_type': 'official',
}
