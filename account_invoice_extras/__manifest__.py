{
    'name': 'Account Invoice Extras',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Unified module for extra invoice fields and settings.',
    'description': '''
    Consolidates functionality for extra invoice fields and printed report configurations.
    
    Features:
    - Carrier Reference Number (Guía de Remisión).
    - Additional Document Reference.
    - Company-level printed invoice footer configuration.
    ''',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'depends': [
        'account',
    ],
    'data': [
        'views/account_move_views.xml',
        'views/res_company_views.xml',
        'reports/report_invoice_document.xml',
    ],
    'icon': '/account_invoice_extras/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 7.0,
    'module_type': 'official',
}
