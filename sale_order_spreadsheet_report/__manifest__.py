{
    'name': 'Sale Order Spreadsheet Report',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Generate Spreadsheet reports for Sale Orders',
    'description': """
This module allows generating dynamic Spreadsheet reports for Sale Orders based on templates.
It adds a configuration in CRM Tags, Sales Teams, and Sale Order Templates to select the default template.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['sale_management', 'crm', 'spreadsheet_edition'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_spreadsheet_template_views.xml',
        'views/sale_order_spreadsheet_views.xml',
        'views/crm_tag_views.xml',
        'views/crm_team_views.xml',
        'views/sale_order_template_views.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'sale_order_spreadsheet_report/static/src/js/sale_order_spreadsheet_action.js',
            'sale_order_spreadsheet_report/static/src/xml/sale_order_spreadsheet_action.xml',
        ],
        'web.assets_backend': [
            'sale_order_spreadsheet_report/static/src/js/sale_order_spreadsheet_loader.js',
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
