{
    'name': 'Voucher Payroll',
    'version': '19.0.1.0.0',
    'category': 'Payroll',
    'summary': """Generates standard employee pay slips without overtime. Tracks worked days, hours, deductions, and net pay for Peruvian payroll compliance.""",
    'description': """
        Voucher Payroll module for Odoo HR Payroll.
        Generates structured pay slip vouchers showing:
        - Worked days classified by type (work, vacation, break, sanctioned, subsidy, medical rest)
        - Regular, nocturnal, compensatory, and overtime hours (25%, 35%, 100%)
        - 3-column salary line layout (Earnings / Deductions / Others)
        - Net pay calculation
        - ISO week number display for the pay period
        - Overtime exclusion mode per employee
        - Employer sign integration
        Fully integrated with Voucher Sending and Holiday Field Payroll modules.
        Compatible with Peruvian payroll regulations.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'live_test_url': 'https://www.ganemo.co/demo',
    'depends': [
        'voucher_sending',
        'employee_service',
        'absence_day',
        'additional_fields_voucher',
        'holiday_field_payroll',
        'types_system_pension'
    ],
    'data': [
        'data/hr_work_entry_type_data_ballots.xml',
        'security/ir.model.access.csv',
        'views/hr_views.xml',
        'views/reports.xml'
    ],
    'icon': '/voucher_payroll/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 175.0,
    'module_type': 'official'
}
