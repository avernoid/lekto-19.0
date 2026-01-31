{
    'name': 'Stock Delivery Portal Backend',
    'version': '19.0.1.0.7',
    'category': 'Inventory/Delivery',
    'summary': 'Backend logic for delivery driver portal',
    'description': """
        Backend module for managing delivery states and driver assignments.
        - Configurable delivery states
        - Driver assignment (Portal Users)
        - Delivery evidence (Signatures, Photos)
        - Automated notifications (Email, WhatsApp)
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'depends': ['stock', 'mail', 'whatsapp', 'portal', 'portal_app_launcher', 'stock_picking_extras'],
    'data': [
        'security/ir.model.access.csv',
        'security/stock_delivery_security.xml',
        'data/stock_delivery_state_data.xml',
        'data/delivery_quick_reply_data.xml',
        'data/portal_app_data.xml',
        'views/stock_delivery_state_views.xml',
        'views/delivery_config_views.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
        'views/delivery_portal_templates.xml',
    ],
    'icon': '/stock_delivery_portal/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 397.0,
    'module_type': 'official',
    'assets': {
        'web.assets_frontend': [
            'stock_delivery_portal/static/src/js/delivery_portal.js',
        ],
    },
}
