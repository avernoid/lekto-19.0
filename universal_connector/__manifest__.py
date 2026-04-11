{
    'name': 'Universal Connector',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Centralized settings hub for third-party connector modules.',
    'description': """
        Universal Connector provides a shared configuration page where all
        connector modules can register their credentials in a single,
        organized place under the Connectors app.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'currency': 'USD',
    'price': 200.0,
}
