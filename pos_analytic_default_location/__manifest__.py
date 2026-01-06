{
    'name': 'POS Analytic Default Location',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Link POS Config to Analytic Distribution Models',
    'description': """
This module extends the analytic distribution rules to include Point of Sale configuration.
It allows you to define default analytic accounts based on the POS Config used for the order.
    """,
    'category': 'Sales/Point of Sale',
    'depends': ['point_of_sale', 'stock_account', 'account_analytic_default_location', 'account_accountant'],
    'data': ['views/account_analytic_distribution_model_views.xml', 'views/account_views.xml'],
    'installable': True,
    'auto_install': False,
    'icon': '/pos_analytic_default_location/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'application': False,
    'currency': 'USD',
    'price': 75.00,
    'module_type': 'official',
}
