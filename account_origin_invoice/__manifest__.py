{
    'name': 'Origen de Documentos Rectificados',
    'icon': '/account_origin_invoice/static/description/icon.png',
    'version': '19.0.1.0.2',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'category': 'Accounting',
    'summary': 'In the credit note identify the invoice for which it was issued',
    'description':""" 
This module adds a section to customer corrective invoices containing fields that store the related Customer invoice information. It also adds the logic for these fields to auto-complete, when using the Create Rectifying Invoice Wizard.
""",
    'depends': [
        'l10n_latam_invoice_document'
    ],
    'data': [
        'views/account_move_views.xml'
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 20.00,
    'images': ['static/description/banner.png'],
    'module_type': 'official'
}
