# -*- coding: utf-8 -*-
{
    'name': 'Ecuador - ATS Sales Retention',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations/Reporting',
    'summary': """Calculates actual valorRetIva and valorRetRenta in the ATS report from customer withholdings.""",
    'description': """Fixes the Ecuadorian ATS report so that valorRetIva and valorRetRenta reflect
the actual withholding amounts received from customers (out_withhold),
instead of always reporting 0.00. Ensures full SRI compliance.""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.com",
    'depends': [
        'l10n_ec_reports_ats',
    ],
    'data': [],
    'icon': '/l10n_ec_ats_sales_retention/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 0.00,
    'module_type': 'official',
}
