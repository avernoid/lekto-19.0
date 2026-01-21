{
    'name': 'Stock Delivery Portal Backend',
    'version': '19.0.1.0.1',
    'summary': 'Backend logic for delivery driver portal',
    'description': """
        Backend module for managing delivery states and driver assignments.
        - Configurable delivery states
        - Driver assignment (Portal Users)
        - Delivery evidence (Signatures, Photos)
        - Automated notifications (Email, WhatsApp)
    """,
    'category': 'Inventory/Delivery',
    'author': 'Ganemo',
    'depends': ['stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/stock_delivery_security.xml',
        'views/stock_delivery_state_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
