{
    'name': 'Sale One Step Invoice',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Skip the invoice wizard and auto-post invoices.',
    'description': """
        This module allows configuring Sales Teams to:
        - Skip the "Create Invoice" wizard and create a draft invoice directly.
        - Automatically post (validate) the created invoice.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['sale', 'sale_management', 'crm'],
    'data': [
        'views/crm_team_views.xml',
        'views/sale_order_views.xml',
    ],
    'icon': '/sale_one_step_invoice/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 93.0,
    'module_type': 'official',
}
