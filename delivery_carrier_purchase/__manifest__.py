{
    'name': 'Carrier Purchase per Shipment',
    'version': '18.0.1.0.1',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Buy the transport of every validated shipment from the real carrier, at its real cost, in an open request for quotation',
    'description': """
When a shipment to a customer (delivery or dropship) is validated, a purchase line for
its transport is added for the vendor of the shipping method, even when the shipping
is free for the customer.

* One line per shipment, grouped in an open request for quotation per vendor and month
  (or week, or day), or one purchase order per shipment.
* Cost of the line: what the carrier returns when the shipment is created, the shipping
  method rules with the real destination, a fixed cost or the vendor price list.
* Description with the transfer, the tracking reference (updated when it arrives later),
  the destination and the weight; links from the transfer to the line and back.
* Never blocks the validation: if the cost cannot be obtained the line is created at 0
  with a note, and if the line cannot be created an activity is left on the transfer.
* Cancelling the shipment at the carrier, or the Cancel Transport Purchase button, never
  deletes the line: its price goes to 0 and its description says CANCELLED.
* Off until enabled in the Inventory settings, with a warning when the delivery product
  still creates purchases by itself (Purchase Automatically).
""",
    'category': 'Inventory/Delivery',
    'depends': [
        'purchase_stock',
        'sale_purchase',
        'stock_delivery_dropship',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_picking_views.xml',
        'views/purchase_order_views.xml',
        'wizard/carrier_purchase_cancel_views.xml',
    ],
    'demo': [
        'demo/delivery_carrier_purchase_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'icon': '/delivery_carrier_purchase/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 69.0,
    'module_type': 'official',
}
