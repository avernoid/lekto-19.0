{
    'name': 'FSM Sale Start Required',
    'version': '19.0.1.0.11',
    'category': 'Services/Field Service',
    'summary': 'Require timer start before adding products to FSM tasks',
    'description': """
        FSM Sale Start Required
        =======================
        Adds a project-level setting "Require Start to Sell" that, when enabled,
        prevents technicians from adding products or materials to a Field Service
        task until they have pressed the Start button (timer started or at least
        one timesheet entry recorded).

        Works seamlessly with both the native FSM products button and any
        third-party buttons that invoke action_fsm_view_material (e.g.,
        fsm_quick_products).
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['industry_fsm_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_project_views.xml',
    ],
    'icon': '/fsm_sale_start_required/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 45.0,
    'module_type': 'official',
}
