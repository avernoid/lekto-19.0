# -*- coding: utf-8 -*-
{
    'name': 'Expense to Invoice Automation',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Automates Vendor Bill creation from HR Expenses for legal reporting compliance',
    'description': """
        Automatically creates Vendor Bills (in_invoice) upon posting HR Expenses.
        - Supports Company Account and Own Account payment modes.
        - Groups separated expenses (split expenses) into a single invoice.
        - Autoreconciles the vendor payables with corresponding receipts or payments.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'license': 'OPL-1',
    'depends': [
        'hr_expense',
        'account',
        'portal',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/hr_expense_views.xml',
        'views/account_move_views.xml',
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'expense_to_invoice_automation/static/src/js/expense_to_invoice_automation_pwa.js',
        ],
    },
    'icon': '/expense_to_invoice_automation/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'currency': 'USD',
    'price': 289.0,
    'module_type': 'official',
    'installable': True,
    'auto_install': False,
    'application': False,
}
