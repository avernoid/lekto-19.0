{
    'name': 'Task Visit Geolocation',
    'version': '19.0.1.0.0',
    'category': 'Project',
    'summary': 'Add geolocation features to project tasks for visit registration',
    'icon': '/task_visit_geolocation/static/description/icon.png',
    'description': """
This module extends project tasks to include geolocation functionalities for visit registration.
- Add a boolean field "Registrar visita con Geolocalización" to project.project.
- Add a numeric field "Distancia máxima permitida (m)" to project.project.
- Add a "Registrar visita" button to project.task.
- Obtain and store geolocation coordinates (latitude, longitude) for visits.
- Calculate distance between current location and client address.
- Warn if outside max distance; otherwise record visit and mark task as done.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',

    'depends': [
        'base',
        'project',
        'fsm_sale_lost_reason',
        'web',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/project_views.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'task_visit_geolocation/static/src/js/task_visit_geolocation.js',
        ],
    },

    'images': [
        'static/description/banner.png',
    ],

    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
    'currency': 'USD',
    'price': 97.0,
    'module_type': 'official',
}
