{
    'name': 'Auto Cancel FSM Task',
    'version': '19.0.1.0.0',
    'category': 'Project',
    'summary': 'Automatically cancel/finish tasks based on antiquity',
    'description': """
        This module adds a feature to automatically mark tasks as done if they are older than a configured number of hours relative to their end date.
        It also flags these tasks as "Not Executed".
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['project'],
    'data': [
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'data/ir_cron_data.xml',
    ],
    'images': ['static/description/banner.svg'],
    'license': 'Other proprietary',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 97.0,
    'module_type': 'official',
    'icon': '/auto_cancel_fsm_task/static/description/icon.svg',
}
