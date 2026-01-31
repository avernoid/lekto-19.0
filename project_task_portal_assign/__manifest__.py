{
    'name': 'Project Task Portal Assignment',
    'version': '19.0.1.0.0',
    'category': 'Services/Project',
    'summary': 'Allow assigning Portal Users to Tasks',

    'description': """
        This module extends Project configuration to allow Portal Users to be assigned to Tasks.
        
        Features:
        - "Allow Portal User Assignment" toggle on Projects (Default: True).
        - Dynamic filter on Task "Assignees" field to include Portal Users when enabled.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['project'],
    'data': [
        'views/project_project_views.xml',
        'views/project_task_views.xml',
    ],
    'installable': True,
    'application': False,
    'icon': '/project_task_portal_assign/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 30.0,
    'module_type': 'official',
}
