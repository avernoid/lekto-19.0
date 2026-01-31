{
    'name': 'Partner Offline Portal',
    'version': '19.0.1.0.1',
    'category': 'Portal',
    'summary': 'PWA Optimized Partner Portal',
    'description': """
        PWA module for accessing partners/contacts in offline mode.
        Features:
        - Mobile-first interface for res.partner
        - Offline capabilities via Service Worker
        - Dynamic PWA Manifest based on Portal App registration
        - Fast "Call" and "Navigate" actions
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['base', 'portal', 'website', 'contacts', 'project', 'sales_team', 'portal_app_launcher'],
    'data': [
        'security/partner_offline_groups.xml',
        'security/ir.model.access.csv',
        'data/portal_app_data.xml',
        'views/partner_portal_templates.xml',
        'views/crm_team_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'partner_offline/static/src/css/style.css',
            'partner_offline/static/src/js/partner_portal.js',
        ],
    },
    'icon': '/partner_offline/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 95.0,
    'module_type': 'official',
}
