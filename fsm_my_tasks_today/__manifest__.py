{
    'name': 'My Visits',
    'version': '19.0.1.0.0',
    'category': 'Field Service',
    'summary': """Your daily field visits at a glance: tasks for today, filtered by user and date.""",
    'description': """
        Standalone app for field service technicians.
        Shows only the logged-in user's FSM tasks scheduled for today.
        Domain-level filters guarantee the user/date restriction — no extra clicks needed.
        Includes an optional "Active Tasks" filter and a map view with drag-and-drop resequencing.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'industry_fsm',
        'project_enterprise',
    ],
    'data': [
        'views/fsm_today_views.xml',
    ],
    'icon': '/fsm_my_tasks_today/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': True,
    'currency': 'USD',
    'price': 45.0,
    'module_type': 'official',
}
