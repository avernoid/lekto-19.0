{
    'name': 'Use Classic Format To Print Invoices',
    'version': '19.0.1.0.1',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'summary': '''
    Add an additional, classic-style invoice format.
    ''',
    'icon': '/classic_format_invoice/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'Description': '''
    Add a classic format for invoices, which is requested by many users
    ''',
    'category': 'Accounting',
    'depends': [
        'account',
        'uom',
        'l10n_latam_invoice_document',
        'amount_to_text_invoice',
        'base_address_extended',
        'account_invoice_extras',
        'l10n_latam_base',
    ],
    'assets': {
        'web.report_assets_common': [
            'classic_format_invoice/static/src/css/main.css',
        ]},
    'data': [
        'views/account_journal_views.xml',
        'reports/classic_invoice_report.xml',
        'reports/classic_invoice_template.xml',
        'reports/modern_template.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'Other proprietary',
    'currency': 'USD',
    'price': 45.00,
    'module_type': 'official'
}
