{
    'name': 'Payment Conditions',  # Short non-technical English name
    'version': '19.0.1.0.1',  # Module version - keep 19.0.X.X.X structure
    'category': 'Human Resources/Payroll',
    'summary': """Define and manage payroll payment conditions: period, type, special situation, and variable remuneration.""",
    'description': """
This module extends Odoo Payroll and HR contracts to manage payment conditions
for employees in Peru. It introduces the following catalogs:
- Payment Period (periodicidad de remuneración)
- Payment Type (tipo de pago)
- Special Situation (situación especial)
- Variable Payment (remuneración variable)

These catalogs are linked to the HR contract version (hr.version) and exposed
on the employee form for HR managers, enabling precise classification of
payroll remuneration conditions according to Peruvian labor law.
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'l10n_pe_localization_menu',
        'hr_payroll',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/payment_period_data.xml',
        'data/payment_type_data.xml',
        'data/special_situation_data.xml',
        'data/variable_payment_data.xml',
        'views/payment_period_menus.xml',
        'views/payment_type_menus.xml',
        'views/special_situation_menus.xml',
        'views/hr_contract_views.xml',
        'views/hr_payroll_structure_type_views.xml',
        'views/hr_payroll_structure_views.xml',
        'views/payment_period_views.xml',
        'views/payment_type_views.xml',
        'views/special_situation_views.xml',
        'views/variable_payment_views.xml',
    ],
    'icon': '/payment_conditions/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 49.0,
    'module_type': 'official',
}
