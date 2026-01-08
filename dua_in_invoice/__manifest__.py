{
    'name': 'DUA in Invoice',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'category': 'Accounting/Accounting',
    'summary': 'Add required fields on purchase invoices to register the DUA as required by the electronic purchase record (PLE).',
    'description': """
This module will create the field called "Year of issue" and "Customs unit" in the supplier invoice when we choose the document type "50" called "SAD".

In the field "Customs Unit" it will give us a list of codes: 019, 028, 046, 055, 082, etc.

*These codes will be loaded in the path "LOCATION/PLE/[11]CUSTOMS DEPENDENCY CODE".
    """,
    'depends': [
        'localization_menu',
        'l10n_latam_invoice_document'
    ],
    'data': [
        'views/account_move_views.xml',
        'data/account_move_data.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 10.00,
    'images': ['static/description/banner.png'],
    'icon': '/dua_in_invoice/static/description/icon.png',
    'module_type': 'official',
}
