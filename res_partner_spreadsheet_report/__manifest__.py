{
    'name': 'Contact Spreadsheet Report',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Generate Spreadsheet reports for Contacts',
    'description': """
This module allows generating dynamic Spreadsheet reports for Contacts based on templates.
It adds a configuration in Contacts and Contact Tags to select the default template.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['base', 'spreadsheet_edition'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_spreadsheet_template_views.xml',
        'views/res_partner_spreadsheet_views.xml',
        'views/res_partner_views.xml',
        'views/res_partner_category_views.xml',
    ],
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'res_partner_spreadsheet_report/static/src/js/res_partner_spreadsheet_action.js',
            'res_partner_spreadsheet_report/static/src/xml/res_partner_spreadsheet_action.xml',
        ],
        'web.assets_backend': [
            'res_partner_spreadsheet_report/static/src/js/res_partner_spreadsheet_loader.js',
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
