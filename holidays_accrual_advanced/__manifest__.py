{
    'name': 'Holidays Accrual Advanced',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Customizable Leave Allocation Calculator with Prorate, Limits and Audit Trail',
    'description': """
Advanced accrual leave allocation engine that replaces the standard Odoo calculator.
Supports three accrual methods (Prorate, Period Start, Period End), three-tier limits
(Accrual per Period, Carryover, Total Balance), and a detailed accruement audit ledger.
Includes a wizard for as-of-date balance projection.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'hr_holidays',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/holidays_accrual_advanced_ir_rule.xml',
        'wizards/hr_leave_allocation_accrual_calculator_views.xml',
        'wizards/hr_leave_allocation_accrual_calculator_accruement_views.xml',
        'views/hr_leave_allocation_menus.xml',
        'views/hr_leave_allocation_views.xml',
        'views/hr_leave_allocation_accruement_views.xml',
    ],
    'icon': '/holidays_accrual_advanced/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 50.00,
    'module_type': 'official',
}