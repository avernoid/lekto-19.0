{
    "name": "Related fields for purchases and sales",
    "version": "19.0.1.0.1",
    "author": "Ganemo",
    "maintainer": "Ganemo",
    "company": "Ganemo",
    "website": "https://www.ganemo.co",
    'category': 'Accounting',
    "summary": "This module will allow us to place the type of document, document series and payment voucher number automatically through the records of purchase and sale invoices.",
    "description": """This module will allow us to place the type of document, document series and payment voucher number automatically through the records of purchase and sale invoices.""",
    "depends": [
        'stock', 
        'l10n_latam_invoice_document',
        'purchase_stock',
        'sale_stock'
    ],
    'data': [
        'views/stock_picking_views.xml'
    ],
    'application': False,
    "installable": True,
    "auto_install": False,
    "license": "OPL-1",
    "currency": "USD",
    "price": 79.00,
    'module_type': 'official',
    'icon': '/invoice_type_document_extension/static/description/icon.png',
    'images': ['static/description/banner.png'],
}
