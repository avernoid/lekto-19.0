{
    'name': 'Invoice Spreadsheet Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Generate Spreadsheet reports for Invoices',
    'description': """
This module allows generating dynamic Spreadsheet reports for Invoices based on templates.
It adds a configuration in Journals and Partners to select the default template.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['account', 'spreadsheet_edition'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_invoice_spreadsheet_template_views.xml',
        'views/account_invoice_spreadsheet_views.xml',
        'views/account_move_views.xml',
        'views/account_journal_views.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'account_invoice_spreadsheet_report/static/src/js/account_invoice_spreadsheet_action.js',
            'account_invoice_spreadsheet_report/static/src/xml/account_invoice_spreadsheet_action.xml',
        ],
        'web.assets_backend': [
            'account_invoice_spreadsheet_report/static/src/js/account_invoice_spreadsheet_loader.js',
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
