{
    'name': 'FSM Quick Products Button',
    'version': '19.0.1.0.1',
    'category': 'Services/Field Service',
    'summary': 'Direct access to FSM products and Sales Orders from the task header, optimized for mobile efficiency.',
    'description': """
This module adds direct access buttons to the products/materials list and the associated Sales Order in FSM tasks.
These buttons are visible in both mobile and desktop views, providing a more accessible
way to manage materials and check orders without having to navigate through the smart buttons menu (⚡).

Main Features:
--------------
- Adds discreet "fa-cubes" (Products) and "fa-shopping-cart" (Sales Order) buttons in the task form header.
- Sales Order icon is context-aware: it only appears when an order is linked.
- Functional equivalence to native smart buttons but with priority visibility.
- Optimized for mobile UX by avoiding collapsible menus.
- No overrides of JS or core functional changes, ensuring stability.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['project', 'sale', 'industry_fsm', 'industry_fsm_stock'],
    'data': [
        'views/project_task_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fsm_quick_products/static/src/scss/fsm_quick_products.scss',
        ],
        'web.assets_tests': [
            'fsm_quick_products/static/tests/tours/fsm_quick_products_tour.js',
        ],
    },
    'icon': '/fsm_quick_products/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 45.0,
    'module_type': 'official'
}
