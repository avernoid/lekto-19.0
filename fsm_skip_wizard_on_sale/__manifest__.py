{
    'name': 'FSM Skip Wizard On Sale',
    'version': '19.0.1.0.20',
    'category': 'Services/Field Service',
    'summary': 'Automatically log time without wizard when a confirmed sale exists',
    'description': """
        FSM Skip Wizard On Sale
        =======================
        Adds a project-level option "Skip Wizard If Sale Exists".

        When enabled, stopping the FSM timer on a task that has a confirmed
        Sale Order will automatically log the elapsed time with the description
        "Automated register", bypassing the confirmation wizard entirely.

        If no confirmed sale order exists, the standard confirmation wizard
        opens normally, preserving the full native flow.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'industry_fsm',
        'industry_fsm_sale',
    ],
    'data': [
        'views/project_project_views.xml',
        'wizard/hr_timesheet_stop_timer_confirmation_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fsm_skip_wizard_on_sale/static/src/views/fsm_task_form/**/*.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'icon': '/fsm_skip_wizard_on_sale/static/description/icon.png',
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 35.0,
    'module_type': 'official',
}
