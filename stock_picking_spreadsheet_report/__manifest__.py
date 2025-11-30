{
    'name': 'Stock Picking Spreadsheet Report',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Generate Spreadsheet reports for Stock Pickings',
    'description': """
This module allows generating dynamic Spreadsheet reports for Stock Pickings based on templates.
It adds a configuration in Partners and Picking Types to select the default template.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['stock', 'spreadsheet_edition'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_spreadsheet_template_views.xml',
        'views/stock_picking_spreadsheet_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
    ],
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'stock_picking_spreadsheet_report/static/src/js/stock_picking_spreadsheet_action.js',
            'stock_picking_spreadsheet_report/static/src/xml/stock_picking_spreadsheet_action.xml',
        ],
        'web.assets_backend': [
            'stock_picking_spreadsheet_report/static/src/js/stock_picking_spreadsheet_loader.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'icon': 'static/description/icon.png',
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 249.0,
    'module_type': 'official',
}
