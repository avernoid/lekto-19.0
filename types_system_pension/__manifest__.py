{
    'name': 'Peru Pension System Types',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': """Manage Peruvian SNP and AFP pension system types, commissions, and AFP caps for accurate payroll.""",
    'description': """
This module creates a complete catalog of Peruvian pension systems (SNP and AFP) registered in Peru
under the Localization menu. It allows managing commission rates (fund, bonus, flow, mixed-flow,
balance) per AFP by date range, as well as the monthly AFP cap (tope AFP). The pension system is
assignable to each employee to enable precise payroll deduction calculations, including CUSPP
tracking for AFP affiliates.
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'l10n_pe_localization_menu',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/pension_system_data.xml',
        'views/comis_system_pension_views.xml',
        'views/hr_employee_views.xml',
        'views/pension_system_menus.xml',
        'views/pension_system_views.xml',
        'views/tope_afp_menus.xml',
        'views/tope_afp_views.xml',
    ],
    'icon': '/types_system_pension/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 30.0,
    'module_type': 'official',
}
