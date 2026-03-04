{
    'name': 'Life insurance management',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'category': 'Payroll',
    'summary': 'This module allows you to manage life insurance policies.',
    'description': """
    This module allows you to manage life insurance policies.
    """,
    'depends': [
        'hr',
        'payroll_field',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/life_insurance_views.xml'
    ],
    'icon': '/life_insurance_management/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 83.0,
    'module_type': 'official',
}
