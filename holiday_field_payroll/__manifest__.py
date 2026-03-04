{
    'name': 'Holiday field payroll',
    'version': '19.0.1.0.0',
    'category': 'Payroll',
    'summary': """Create the group of basic rules necessary for the calculation of regular payroll""",
    'description': """
    Regular payroll calculation requires the monthly salary, which is the total salary stipulated in 
    the employee's contract; the daily rate, calculated by dividing the monthly salary by the number 
    of working days in the month; and the hourly rate, determined by dividing the daily rate by the 
    standard number of work hours per day. Standard working hours must be defined, and any hours worked 
    beyond these are considered overtime and are usually compensated at a higher rate.
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['holiday_process'],
    'data': ['views/hr_payslip_views.xml'],
    'icon': '/holiday_field_payroll/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 45.0,
    'module_type': 'official',
}
