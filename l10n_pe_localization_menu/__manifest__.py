{
    'name': 'l10n_pe_localization_menu',
    'version': '19.0.1.0.1',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'category': 'Human Resources/Payroll',
    'summary': 'Creates the main menus for the peruvian localization',
    'description':""" 
This module has been crafted to implement new menus, aiming to enhance key functionalities. It focuses on efficiently managing account detractions and retentions, while also offering organized views for customs codes. With a clear emphasis on optimizing processes, this module serves to elevate and streamline operations in HR, payroll, and compliance.
    """,
    'depends': [
        'account'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/localization_menus.xml',
        'views/account_spot_detraction_menus.xml',
        'views/account_spot_detraction_views.xml',
        'views/account_spot_retention_menus.xml',
        'views/account_spot_retention_views.xml',
        'views/code_aduana_menus.xml',
        'views/code_aduana_views.xml'
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'images': ['static/description/banner.png'],
    'icon': '/l10n_pe_localization_menu/static/description/icon.png',
    'currency': 'USD',
    'price': 20.00,
    'module_type': 'official'
}
