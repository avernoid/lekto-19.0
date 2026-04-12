{
    'name': 'SaaS Portal',
    'version': '19.0.1.0.1',
    'category': 'Services',
    'summary': """Customer portal for SaaS instance management.""",
    'description': """
        Provides portal views for customers to manage their SaaS instances:
        view status, metrics, credentials, environment variables, and
        perform actions like restart.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'saas_orchestrator',
        'portal',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/saas_security.xml',
        'views/portal_templates.xml',
    ],
    'icon': '/saas_portal/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 993.0,
    'module_type': 'official',
}
