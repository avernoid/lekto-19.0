{
    'name': 'FSM Quick Products Button',
    'version': '19.0.1.0.0',
    'category': 'Services/Field Service',
    'summary': 'Direct access to FSM products list from the task header, optimized for mobile efficiency.',
    'description': """
This module adds a direct access button to the products/materials list in FSM tasks.
The button is visible in both mobile and desktop views, providing a more accessible
way to manage materials without having to navigate through the smart buttons menu (⚡).

Main Features:
--------------
- Adds a discreet "fa-cubes" button in the task form header.
- Functional equivalence to the standard "Products" smart button.
- Visibility can be toggled via Odoo Studio.
- Optimized for mobile UX.
- No overrides of JS or core functional changes.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['project', 'industry_fsm', 'industry_fsm_stock'],
    'data': [
        'views/project_task_views.xml',
    ],
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
