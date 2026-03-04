{
    'name': 'Holiday Process',
    'version': '19.0.1.1.0',
    'category': 'Payroll',
    'summary': 'Manage employee vacation processes: track earned, taken, and pending days. Generate assignments and calculate proportional vacations.',
    'description': """
        Adds a 'Vacation & Allowances' tab to the employee form showing a real-time summary of
        computed, taken, and pending vacation days per allocation.
        Provides wizard-based tools to mass-generate leave allocations with proportional calculation
        based on the employee's work calendar, and to process vacation sale and purchase petitions
        integrated with payroll.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'employee_service',
        'holidays_accrual_advanced',
        'hr_payroll',
        'hr_work_entry_holidays',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_holidays_security.xml',
        'data/hr_work_entry_type_data.xml',
        'data/hr_leave_accrual_plan_data.xml',
        'data/hr_leave_type_data.xml',
        'wizard/holiday_generator_wizard.xml',
        'wizard/holiday_petition_wizard.xml',
        'wizard/holiday_update_wizard.xml',
        'views/hr_employee_views.xml',
        'views/hr_leave_allocation_views.xml',
        'views/hr_leave.xml',
        'views/hr_leave_type_views.xml',
    ],
    'icon': '/holiday_process/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 320.00,
    'module_type': 'official',
}