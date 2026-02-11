{
    'name': 'Use classic format to print stock picking',
    'version': '19.0.1.0.5',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'live_test_url': 'https://www.ganemo.co/demo',
    'summary': 'Add an additional, classic-style stock picking peruvian format.',
    'description': """
    Add a peruvian classic format for stock picking, which is requested by many users.
    Standardized design for Delivery Guides (Guía de Remisión).
    """,
    'category': 'Warehouse',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'icon': '/l10n_pe_classic_format_picking/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'depends': [
        'account',
        'stock',
        'stock_picking_print_note',
        'invoice_type_document_extension',
        'third_parties_delivery',
        'l10n_pe_edi_stock',
    ],
    'assets': {'web.report_assets_common':
                   ['l10n_pe_classic_format_picking/static/src/css/main.css']},
    'data': [
        "reports/ticket_report.xml",
        "reports/ticket_template.xml",
        "views/res_config_settings_views.xml",
        "views/stock_picking_type_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 179.00,
    'module_type': 'official'
}