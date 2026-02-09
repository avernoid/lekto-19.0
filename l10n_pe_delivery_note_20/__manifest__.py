{
    'name': 'Peruvian - Electronic Delivery Note extension',
    'version': '19.0.2.0.2',
    'author': 'Ganemo',
    'license': 'OPL-1',
    'website': 'https://www.ganemo.com',
    'maintainer': 'Ganemo',
    'installable': True,
    'auto_install': False,
    'summary': 'extend Odoo native functions for electronic waybill - sender',
    'description': """
The scope of this module is to improve functionalities of the Electronic Referral Guide - Sender.
    """,
    'live_test_url': 'https://www.ganemo.co/demo',
    'category': 'Inventory',
    'icon': '/l10n_pe_delivery_note_20/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'depends': [
        'stock',
        'l10n_pe_edi_stock',
        'third_parties_delivery',
        'tributary_address_extension'
    ],
    'data': [
        'data/edi_delivery_guide.xml',
        'views/stock_picking_views.xml',
        'views/stock_picking_views_button.xml',
        'views/report_deliveryslip.xml',
        'views/res_config_settings_views.xml'
    ],
    'currency': 'USD',
    'module_type': 'official',
    'price': 250.00
}
