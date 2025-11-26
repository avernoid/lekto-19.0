{
    'name': 'Partner Current Location',
    'version': '19.0.1.0.0',
    'category': 'Contacts',
    'summary': 'Get partner coordinates from device current location',
    'description': """
Get partner geolocation coordinates from device GPS/location instead of address.
Useful when visiting clients on-site for more accurate coordinates.
    """,
    'author': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'images': ['static/description/banner.png'],
    'icon': '/partner_current_location/static/description/icon.png',
    'depends': [
        'base',
        'contacts',
        'base_geolocalize',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'partner_current_location/static/src/js/partner_location_action.js',
        ],
    },
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}