{
    'name': 'Financial Statement Annexes Enterprise',
    'version': '19.0.1.0.1',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Native Odoo Enterprise Reporting for Financial Annexes',
    'category': 'Accounting',
    'depends': [
        'financial_statement_annexes',
        'account_reports',
    ],
    'assets': {
        'web.assets_backend': [
            'financial_statement_annexes_enterprise/static/src/**/*',
        ],
    },
    'data': [
        'data/account_financial_report_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'module_type': 'official',
    'price': 120.00,
    'icon': '/financial_statement_annexes_enterprise/static/description/icon.png',
    'images': ['static/description/banner.png'],
}
