{
    'name': 'Dropship shipping with carriers',
    'version': '18.0.1.1.1',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Real sender and recipient of a dropship for carrier integrations',
    'description': """
In a native dropship the contact of the transfer is the vendor and the real delivery
address lives on the purchase order. This module exposes the real recipient (purchase
delivery address) and the real sender (the vendor) of a dropship so carrier connectors
can create the shipment from the dropship, and lets the Dropship operation type print
labels (so the shipment is sent to the carrier when the dropship is validated).

Optional, per operation type: dropships get the shipping method of the sale order, as
deliveries from the warehouse already do (Use Sale Order Carrier). Off by default.
""",
    'category': 'Inventory/Delivery',
    'depends': [
        'stock_delivery',
        'stock_dropshipping',
    ],
    'data': [
        'views/stock_picking_type_views.xml',
    ],
    'demo': [
        'demo/stock_delivery_dropship_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'icon': '/stock_delivery_dropship/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 39.0,
    'module_type': 'official',
}
