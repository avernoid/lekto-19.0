{
    'name': 'HR Localization Menu',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': """Centralized parent menu for all region-specific Payroll localization settings and reports.""",
    'description': """Adds a dedicated 'Localización' parent menu to Odoo Payroll, exclusively visible to Payroll
Managers. Acts as the structural anchor for all country-specific payroll sub-modules (EPS, AFP,
Pension System, Work Occupation, Life Insurance, etc.). Multi-country compatible.""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'hr_payroll',
    ],
    'data': [
        'views/l10n_pe_hr_menus.xml',
    ],
    'icon': '/hr_localization_menu/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 30.00,
    'module_type': 'official',
}
