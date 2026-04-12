{
    'name': 'Openclaw Connector',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Openclaw integration settings for Universal Connector.',
    'description': """
        Adds an Openclaw configuration section to the Universal Connector
        settings page. Configure your Openclaw API credentials from a single,
        centralized location.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['universal_connector'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'icon': '/openclaw_connector/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 249.0,
    'module_type': 'official',
}
