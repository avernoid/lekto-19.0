{
    'name': 'Auto Invoice on Delivery',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Create invoices directly from delivery orders',
    'description': """
This module allows creating invoices directly from the Stock Picking (Delivery) view.
It adds configuration to the Operation Type to:
1. Enable "Emitir Factura" (Create Invoice) button on the picking.
2. Optionally trigger the invoice creation automatically after validation ("Al Validar").

It leverages the Sales Order associated with the picking to generate the invoice,
mimicking the "Create Invoice" flow from the Sales Order.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['stock', 'sale', 'sale_stock'],
    'data': [
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
    ],
    'icon': '/auto_invoice_on_delivery/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 49.0,
    'module_type': 'official'
}
