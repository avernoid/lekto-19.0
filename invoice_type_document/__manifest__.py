{
    'name': 'Place invoice data in reconciliations',
    'version': '19.0.1.0.1',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'category': 'Accounting',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'summary': 'Automatic Document Data in Reconciliations',
    'description': """
This module allows placing the document type, document series and payment receipt number automatically through the reconciliations.
It propagates the document series and number (Serie-Correlativo) from invoices/payments to their journal entry lines,
facilitating the identification of documents during reconciliation.
""",
    'depends': [
        'account', 
        'l10n_latam_invoice_document'
    ],
    'data': [
        'views/account_move_line_views.xml',
        'views/account_move_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 25.00,
    'module_type': 'official',
    'icon': '/invoice_type_document/static/description/icon.svg',
    'images': ['static/description/banner.svg'],

}
