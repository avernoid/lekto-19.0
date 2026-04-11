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
    'website': 'https://www.ganemo.co',
    'depends': ['universal_connector'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'currency': 'USD',
    'price': 1913.0,
}
