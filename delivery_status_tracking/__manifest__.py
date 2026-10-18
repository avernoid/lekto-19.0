{
    'name': 'Delivery Status Tracking – Carriers & Drivers',
    'version': '18.0.1.1.0',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Know where every delivery is: recorded, in transit, delivered or incident, from the carrier or set by hand',
    'description': """
Adds a delivery status to transfers, with configurable states, its date and history.

* Configurable delivery states with a technical code (recorded, in transit, delivered, incident, cancelled...) and a result type (success, partial, failure).
* Carrier integrations update the status automatically through a simple hook; a scheduled action asks them periodically.
* The status can also be set by hand for carriers without integration.
* Optional email template per state.
* Delivery date stored when the delivery reaches a final state.
* Simulation mode per shipping method for demos and training: fictitious tracking numbers and statuses, nothing sent to the carrier.
""",
    'category': 'Inventory/Delivery',
    'depends': [
        'stock_delivery',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/stock_delivery_state_data.xml',
        'data/ir_cron_data.xml',
        'views/stock_delivery_state_views.xml',
        'views/stock_picking_views.xml',
        'views/delivery_carrier_views.xml',
    ],
    'demo': [
        'demo/delivery_status_tracking_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'icon': '/delivery_status_tracking/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 79.0,
    'module_type': 'official',
}
