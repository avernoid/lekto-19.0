{
    'name': 'Absence Day',
    'version': '19.0.4.0.0',
    'category': 'Human Resources',
    'summary': """Adds extra work entry types for absence tracking.""",
    'description': """Adds three additional work entry types used for absence and payroll tracking:
- Days off (WORKD): For weekly rest days (DSO)
- Global Leave (WORKG): For public holidays
- Night shift (WORKN): For night shift entries""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['hr_payroll'],
    'data': [
        'data/hr_work_entry_type_data.xml',
        'data/hr_leave_type_data.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_work_entry_type_views.xml',
        'views/resource_calendar_views.xml',
    ],
    'icon': '/absence_day/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 1.0,
    'module_type': 'official',
}
