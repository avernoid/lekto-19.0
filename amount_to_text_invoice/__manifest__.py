{
    'name': 'Amount To Text Invoice',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Convert invoice totals to text. Force Uppercase, Language, and Strict Formats.',
    'description': """
This module extends the native Odoo functionality to convert invoice amounts to text.
It allows configuring per Journal:
- Force Amount in Uppercase (e.g. ONE HUNDRED).
- Force specific Language (overriding Partner language).
- Choose format: Native Odoo or Custom Strict (00/100).
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'account'
    ],
    'external_dependencies': {
        'python': ['num2words'],
    },
    'data': [
        'views/account_journal_views.xml',
    ],
    'icon': '/amount_to_text_invoice/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 50.00,
    'module_type': 'official'
}
