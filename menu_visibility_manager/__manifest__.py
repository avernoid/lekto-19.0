{
    'name': 'Menu Visibility Manager',
    'version': '19.0.2.0.0',
    'category': 'Extra Tools',
    'summary': 'Hide specific menu items for selected users.',
    'description': """
Menu Visibility Manager
=======================
This module allows administrators to hide specific menu items for certain users.

Features:
- Hide menus per user.
- Exclude users per menu.
- Bi-directional synchronization (shared configuration).
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['base'],
    'data': [
        'views/res_users_views.xml',
        'views/ir_ui_menu_views.xml',
    ],
    'icon': '/menu_visibility_manager/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 53.0,
    'module_type': 'official',
}
