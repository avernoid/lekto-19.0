{
    'name': 'Force Exchange Rate',
    'version': '19.0.2.0.1',
    'category': 'Accounting',
    'summary': 'Manually force specific exchange rates on Payments and Journal Entries.',
    'description': """
Force Exchange Rate
===================
This module allows users to manualy override the system's exchange rate on Payments and Journal Entries.
It ensures that the forced rate is respected during the journal entry creation and line computation, preventing the default daily rate from being applied when a specific transaction rate is required (e.g., Spot Rates, Tax Detractions).

Key Features:
- 'Force T.C.' field on Register Payment Wizard.
- 'Force T.C.' field on Manual Payments (with Auto-complete).
- Safeguard logic for Manual Entries (prevents 0.00).
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/account_payment_register_views.xml',
    ],
    'icon': '/account_field_to_force_exchange_rate/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 150.00,
    'module_type': 'official',
}
