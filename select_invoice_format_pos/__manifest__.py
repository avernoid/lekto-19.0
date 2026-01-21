{
    'name': 'Select Invoice Format POS',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Select the invoice to print at the POS',
    'description': """
This module adds the invoice format that you want to use for the POS and adds a button 
at the end of the payment to be able to manually print said configured invoice.
""",
    'category': 'Sales/Point of Sale',
    'depends': [
        'pos_ticket_base_template',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'select_invoice_format_pos/static/src/**/*',
        ],
    },
    'icon': '/select_invoice_format_pos/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 45.00,
    'module_type': 'official',
}
