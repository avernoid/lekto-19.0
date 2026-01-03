{
    'name': 'Stock Batch Spreadsheet Report',
    'version': '19.0.1.0.6',
    'category': 'Inventory/Inventory',
    'summary': 'Generate Spreadsheet reports for Batch Pickings',
    'description': """
This module allows generating dynamic Spreadsheet reports for Batch Pickings based on templates.
It adds a configuration in Operation Types to select the default template.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['stock_picking_batch', 'spreadsheet_edition'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_batch_spreadsheet_template_views.xml',
        'views/stock_batch_spreadsheet_views.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_picking_batch_views.xml',
    ],
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'stock_batch_spreadsheet_report/static/src/js/stock_batch_spreadsheet_action.js',
            'stock_batch_spreadsheet_report/static/src/xml/stock_batch_spreadsheet_action.xml',
        ],
        'web.assets_backend': [
            'stock_batch_spreadsheet_report/static/src/js/stock_batch_spreadsheet_loader.js',
        ],
    },
    'icon': '/stock_batch_spreadsheet_report/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 249.0,
    'module_type': 'official',
}
