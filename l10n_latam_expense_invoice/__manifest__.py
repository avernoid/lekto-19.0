# -*- coding: utf-8 -*-
{
    'name': 'LatAm Expense Invoice Automation',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Bridge module to include LatAm document types in automated expense vendor bills',
    'description': """
        Adds LatAm document type and number to HR Expenses and automatically passes them to the Vendor Bill generated.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'hr_expense',
        'expense_to_invoice_automation',
        'l10n_latam_invoice_document',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/hr_expense_views.xml',
    ],
    'icon': '/l10n_latam_expense_invoice/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 149.00,
    'module_type': 'official',
}
