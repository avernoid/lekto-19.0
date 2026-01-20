{
    'name': 'POS Ticket Base Template',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'category': 'Sales/Point of Sale',
    'summary': 'Technical module to centralize the overwriting of POS functionalities',
    'description': """
This module is technical with the purpose of creating a base module to centralize the overwriting of POS functionalities.
""",
    'depends': [
        'point_of_sale'
    ],
    'data': [
        'views/res_config_settings_views.xml'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_ticket_base_template/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_ticket_base_template/static/tests/tours/**/*',
        ],
        'point_of_sale.assets_debug': [
            'pos_ticket_base_template/static/tests/tours/**/*',
        ],
    },
    'icon': '/pos_ticket_base_template/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 40.00,
    'module_type': 'official'
}
