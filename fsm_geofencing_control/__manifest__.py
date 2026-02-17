{
    'name': 'FSM Geofencing Control',
    'version': '18.0.1.0.0',
    'category': 'Services/Field Service',
    'summary': 'Control technician location when starting/stopping FSM timers',
    'description': """
        FSM Geofencing Control
        ======================
        This module extends Field Service Management with geofencing capabilities:
        
        - Validate technician distance from customer when starting timer
        - Validate technician distance from customer when stopping timer
        - Require lost reason when stopping without confirmed sale order
        - Auto-mark tasks as done when logging time
        - Track last known technician location on tasks
        
        Integrates seamlessly with Odoo's native geolocation features.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': [
        'industry_fsm',
        'fsm_sale_lost_reason',
        'base_geolocalize',
        'timesheet_grid',
    ],
    'data': [
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'wizard/project_task_create_timesheet_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'fsm_geofencing_control/static/src/views/fsm_task_form/**/*.js',
            'fsm_geofencing_control/static/src/views/project_task_create_timesheet_wizard/**/*.js',
        ],
    },
    'icon': '/fsm_geofencing_control/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 213.0,
    'module_type': 'official'
}
