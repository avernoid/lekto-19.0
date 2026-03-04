{
    'name': 'Partner Concept',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Manage salary concepts individually for employees.',
    'description': """This module allows you to manage salary concepts individually for employees.""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'hr_payroll'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_partner_concept_views.xml',
        'views/hr_employee_views.xml'
    ],
    'icon': '/partner_concept/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 39.00,
    'module_type': 'official',
}
