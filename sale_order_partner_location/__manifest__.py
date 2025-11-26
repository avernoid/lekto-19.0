{
    'name': 'Sale Order Partner Location',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Capture location when creating/confirming sales orders',
    'description': """
Sale Order Partner Location
============================
Capture geolocation coordinates when creating or confirming sales orders.
Features:
- Update partner location from current device location
- Register sale location at confirmation
- Auto-capture location when confirming sale (configurable)
- View location on Google Maps
- Configurable per Sales Team
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'base',
        'sale',
        'sale_management',
        'partner_current_location',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_team_views.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_order_partner_location/static/src/js/sale_location_action.js',
        ],
    },
    'icon': '/sale_order_partner_location/static/description/icon.svg',
    'images': ['static/description/banner.svg'],
    'license': 'Other proprietary',
    'installable': True,
    'application': False,
    'auto_install': False,
    'currency': 'USD',
    'price': 45.0,
    'module_type': 'official',
}