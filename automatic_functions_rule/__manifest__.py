{
    'name': 'Automatic Functions Rule',
    'version': '19.0.1.0.1',
    'category': 'Payroll',
    'summary': """Automatically removes zero-value salary lines, worked days, and input entries from payslips after computation.""",
    'description': """Validates salary rules, worked days, and input entries on hr.payslip that result in zero values
and removes them automatically. Adds an 'Eliminate Zeros' button for manual cleanup. Also injects input line types
from the salary structure into the payslip for easy data entry.""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'hr_payroll',
    ],
    'data': [
        'views/hr_payslip.xml',
    ],
    'icon': '/automatic_functions_rule/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 20.00,
    'module_type': 'official',
}