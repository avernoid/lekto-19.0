{
    'name': 'Identification type employee',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'category': 'Payroll',
    'summary': 'This module creates in employees a field called Document Type which allows you to identify the type of document that corresponds to your employees',
    'description': """
This module creates a field called Document Type in employees, 
which allows you to identify the type of document that corresponds to your employees.
Provides the possibility of specifying the specific type of document that corresponds
to each employee within the system.
""",
    'depends': [
        'hr',
        'l10n_latam_base',
        'document_type_validation'
    ],
    'data': ['views/hr_views.xml'],
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 20.0,
    'module_type': 'official',
    'icon': '/identification_type_employee/static/description/icon.png',
    'images': ['static/description/banner.png']
}
