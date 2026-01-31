{
    'name': 'Portal App Launcher',
    'version': '19.0.1.0.3',
    'category': 'Portal',
    'summary': 'Mobile-First App Launcher for Portal Users',
    'description': """
Provides a professional, app-like landing page for Odoo Portal users. 
Key features:
- PWA Ready: Installable on Home Screen.
- One-Hand UX: Bottom navigation and thumb-friendly grid.
- Modular: Other modules can register custom "Apps" (e.g., Photos, Jobs).
- Lightweight & Secure.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['portal', 'website'],
    'data': [
        'security/portal_app_security.xml',
        'security/ir.model.access.csv',
        'data/standard_portal_app_data.xml',
        'views/portal_app_views.xml',
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'portal_app_launcher/static/src/css/portal_launcher.css',
        ],
    },
    'icon': '/portal_app_launcher/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 45.0,
    'module_type': 'official',
}
