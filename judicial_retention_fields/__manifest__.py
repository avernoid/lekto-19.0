{
    'name': 'Judicial retention fields',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'category': 'Payroll',
    'summary': 'Allows management of withholdings by judicial process of employees',
    'description': """
This module allows the management of withholdings by judicial process of employees.
    """,
    'depends': [
        'additional_fields_voucher',
        'payment_conditions',
        'type_bank_accounts'
    ],
    'data': [
        'views/report.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 83.0,
    'module_type': 'official',
    'icon': '/judicial_retention_fields/static/description/icon.png',
    'images': ['static/description/banner.png'],
}
