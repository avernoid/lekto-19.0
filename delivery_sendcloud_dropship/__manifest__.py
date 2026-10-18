{
    'name': 'Sendcloud: dropship shipments and delivery states',
    'version': '18.0.1.2.2',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Ship dropships with Sendcloud (pickup at the vendor) and update the delivery state of the transfer',
    'description': """
Extends the official Sendcloud connector (delivery_sendcloud):

* Dropship: the parcel is created with the vendor as sender and the purchase delivery address as recipient (the official connector uses the warehouse and the vendor).
* Recipient email and phone fall back to the company of the address and to the customer of the sale order (carriers such as UPS require the email).
* Optional Sendcloud contract per shipping method, and optional sender address taken from Odoo instead of the Sendcloud sender addresses.
* Delivery state of the transfer (delivery_status_tracking) updated from the Sendcloud parcel status: recorded, in transit, delivered, incident, cancelled.
* Simulation for demos and training (Simulate Carrier Integration on the shipping method): the connector runs completely against a simulated Sendcloud API, with label, tracking number and statuses, without any call to Sendcloud.
""",
    'category': 'Inventory/Delivery',
    'depends': [
        'delivery_sendcloud',
        'delivery_status_tracking',
        'stock_delivery_dropship',
    ],
    'data': [
        'views/delivery_carrier_views.xml',
    ],
    'demo': [
        'demo/delivery_sendcloud_dropship_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'icon': '/delivery_sendcloud_dropship/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 149.0,
    'module_type': 'official',
}
