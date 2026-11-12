{
    'name': 'Portal Navigation Sidebar',
    'version': '19.0.1.3.0',
    'category': 'Website/Website',
    'summary': """Persistent left menu on every customer portal list page, built from the apps you have installed.""",
    'description': """
Portal Navigation Sidebar
=========================

Adds a navigation menu to the customer portal pages (invoices, orders,
tickets, projects, addresses, payment methods...). The menu shows the same options as the
portal home page, in the same order, so customers can jump from one section
to another without going back to the home page.

* No configuration: options come from the installed apps.
* Sections without documents stay hidden, like on the home page.
* The current section is highlighted.
* Left menu on desktop; on mobile, a button opens it as a side panel.
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': [
        'portal',
    ],
    'data': [
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'portal_navigation_sidebar/static/src/scss/portal_navigation.scss',
            'portal_navigation_sidebar/static/src/interactions/portal_navigation.js',
        ],
    },
    'icon': '/portal_navigation_sidebar/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 49.0,
    'module_type': 'official',
}
