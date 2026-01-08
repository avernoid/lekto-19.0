{
    'name': 'Unrealized gains and losses for foreign currency',
    # [V19 Migration] Updated version to 19.0.1.0.0
    'version': '19.0.1.0.1',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': "Adjusts the gain and loss for unrealized exchange rate difference.",
    'description': """
    Calculates the exchange rate difference of the accounting accounts in foreign currency and records the accounting 
    entry for the difference automatically. Allows you to set different exchange rates for the same currency, for different 
    accounts. Which is very useful if the exchange rate for accounting Assets and Liabilities differs in your country.
    """,
    'category': 'Accounting',
    'depends': ['financial_statement_annexes'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/wizard_report_financial_currency_views.xml',
    ],
    'icon': '/financial_statement_annexes_currency/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 159.00,
    'module_type': 'official',
}
