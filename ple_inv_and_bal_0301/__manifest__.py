{
    'name': 'PLE 3.1 Balance Sheet - Statement of Financial Position',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': """Generate SUNAT PLE Format 3.1 (Statement of Financial Position) with Excel, TXT and PDF reports.""",
    'description': """
This module generates the PLE Format 3.1 "Statement of Financial Position" (Estado de Situación Financiera)
for the electronic inventory and balance book required by SUNAT in Peru.

Features:
- Multi-format output: Excel, TXT, and PDF reports
- 4-level EEFF hierarchy with detailed sub-categories in PDF
- Automatic initial balance calculation
- Configurable EEFF-account mapping via wizard
- Multi-company isolation via record rules
- Automatic period defaults (previous year)
- Date validation constraints
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'ple_sale_book',
        'l10n_pe_catalog',
        'ple_cash_book',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/eeff_ple_data.xml',
        'data/ple_eeff_account_config_data.xml',
        'reports/ple_inv_bal_report.xml',
        'reports/ple_inv_bal_template.xml',
        'views/account_account_views.xml',
        'views/account_move_line_views.xml',
        'views/account_move_views.xml',
        'views/eeff_ple_menus.xml',
        'views/eeff_ple_views.xml',
        'views/ple_eeff_account_config_views.xml',
        'views/ple_inv_bal_initial_balances_views.xml',
        'views/ple_report_inv_bal_menus.xml',
        'views/ple_report_inv_bal_views.xml',
        'wizard/ple_update_eeff_wizard_views.xml',
        'sql/eeff_ple.sql',
    ],
    'icon': '/ple_inv_and_bal_0301/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 35.00,
    'module_type': 'official',
}
