{
    'name': 'Employee Service',
    'version': '19.0.2.0.0',
    'category': 'Human Resources',
    'summary': 'Manage employee service duration, hire date and tenure automatically.',
    'description': """
This module calculates employee service duration based on contracts/versions history.
It tracks:
- Service Hire Date (from oldest active version)
- Service Start Date
- Exact Service Tenure (Years, Months, Days) -> Uses native Contract End Date
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'hr',
    ],
    'data': [
        'views/hr_employee_views.xml',
    ],
    'icon': '/employee_service/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 30.00,
    'module_type': 'official'
}
