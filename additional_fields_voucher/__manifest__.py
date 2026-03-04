{
    'name': 'Additional Fields Voucher',
    'version': '19.0.1.0.0',
    'category': 'Payroll',
    'summary': 'Adds the employee signature field in the HR configuration tab.',
    'description': """
This module adds the employee signature field in the HR configuration tab, 
allowing it to be easily referenced and printed on payroll vouchers.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'hr_payroll',
        'identification_type_employee'
    ],
    'data': [
        'views/hr_employee_views.xml',
        'views/hr_payroll_structure_views.xml',
    ],
    'icon': '/additional_fields_voucher/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 30.00,
    'module_type': 'official'
}
