{
    'name': 'Base Spot',
    'version': '19.0.1.0.1',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'category': 'Localization',
    'summary': 'Add fields for legal deductions',
    'description': """
Create additional fields on purchase invoices that allow you to identify if an invoice is affected by legal deductions, the type of deduction, the payment date of the deduction and the payment operation code of the deduction.
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'depends': [
        'l10n_pe_localization_menu'
    ],
    'data': [
        'data/account_spot_detraction_data.xml',
        'views/account_move_views.xml',
        'views/account_spot_detraction_views.xml'
    ],
    'icon': '/base_spot/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'application': False,
    'installable': True,
    'auto_install': False,
    'currency': 'USD',
    'price': 10.00,
    'module_type': 'official'
}
