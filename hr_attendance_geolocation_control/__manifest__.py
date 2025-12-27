# -*- coding: utf-8 -*-
{
    'name': 'Attendance Geolocation Control',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': """Validate attendance location using high-precision geolocation and automated policies.""",
    'description': """
Attendance Geolocation Control
==============================
Ensure employees check in from the correct workplace with advanced geolocation validation.

Features:
---------
- Real-time geofencing validation based on work location coordinates.
- Flexible enforcement policies (Block, Allow with Reason, Allow and Mark).
- GPS Accuracy filtering to prevent location spoofing.
- Full integration with Odoo native attendance flow and hr_homeworking.
- HR audit tools with specialized views for distance and reliability tracking.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.com",
    'depends': [
        'hr_attendance',
        'hr_homeworking',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_work_location_views.xml',
        'views/hr_job_views.xml',
        'views/res_company_views.xml',
        'views/hr_attendance_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_attendance_geolocation_control/static/src/systray/attendance_menu.js',
            'hr_attendance_geolocation_control/static/src/components/*/*.xml',
        ],
    },
    'icon': 'hr_attendance_geolocation_control/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 149.0,
    'module_type': 'official'
}
