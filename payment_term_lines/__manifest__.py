{
    'name': 'Payment term lines',
    'version': '19.0.1.0.2',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Calculate due dates based on Accounting Date and handle Detractions/Retentions separately.',
    'category': 'Accounting',
    'depends': ['account'],
    'data': [
        'views/payment_line_view.xml',
        'views/account_views.xml'
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 100.00,
    'module_type': 'official',
    'icon': '/payment_term_lines/static/description/icon.png',
    'images': ['static/description/banner.png'],
}
