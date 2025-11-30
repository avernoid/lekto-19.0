{
    'name': 'MRP Production Spreadsheet Report',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Generate Spreadsheet reports for Manufacturing Orders',
    'description': """
This module allows generating dynamic Spreadsheet reports for Manufacturing Orders based on templates.
It adds a configuration in Bills of Materials and Picking Types to select the default template.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['mrp', 'spreadsheet_edition'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_production_spreadsheet_template_views.xml',
        'views/mrp_production_spreadsheet_views.xml',
        'views/mrp_bom_views.xml',
        'views/stock_picking_type_views.xml',
        'views/mrp_production_views.xml',
    ],
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'mrp_production_spreadsheet_report/static/src/js/mrp_production_spreadsheet_action.js',
            'mrp_production_spreadsheet_report/static/src/xml/mrp_production_spreadsheet_action.xml',
        ],
        'web.assets_backend': [
            'mrp_production_spreadsheet_report/static/src/js/mrp_production_spreadsheet_loader.js',
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
