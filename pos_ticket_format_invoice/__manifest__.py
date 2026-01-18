{
    'name': 'Pos Ticket Format Invoice',
    'version': '19.0.1.0.2',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'category': 'Accounting/Point of Sale',
    'summary': 'Add an additional format to invoices POS ticket type which allows the use of thermal printers',
    'description': """
This module creates a new Ticket Type Format to use in printing the Invoice, in this way thermal printers can be used to print the receipts.
""",
    'depends': [
        'account',
        'l10n_latam_invoice_document',
        'account_invoice_extras',
        'amount_to_text_invoice',
        'base_address_extended',
        'l10n_latam_base',
    ],
    'data': [
        'reports/invoice_ticket_report.xml',
        'reports/invoice_ticket_templates.xml',
        'views/account_journal_views.xml'
    ],
    'assets': {
        'web.report_assets_common': [
            'pos_ticket_format_invoice/static/src/css/main.css',
        ],
    },
    'icon': '/pos_ticket_format_invoice/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 45.00,
    'module_type': 'official'
}
