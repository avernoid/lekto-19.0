{
    'name': 'Electronic Invoicing Peru',
    'version': '19.0.1.0.1',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'live_test_url': 'https://www.ganemo.co/demo',
    'summary': 'Electronic Invoicing Peru with OSE integration, Type 13 credit notes, and SPOT support.',
    'description': """
Electronic Invoicing Peru
=========================

This module implements advanced Electronic Invoicing features for Peru, including:
- **OSE Integration**: Connect directly with Digiflow or SUNAT web services.
- **Correction Credit Notes (Type 13)**: Correct payment terms and amounts without cancelling invoices.
- **Advanced Tax Logic**: Native support for 'Gratuita' (Free) and 'Bonificaciones' (Bonus) items.
- **SPOT / Detractions**: Automated handling of detraction threshold and payment terms.
- **Error Handling**: Captures SUNAT XML errors and attaches them for easier debugging.
    """,
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'l10n_pe_edi',
        'payment_term_lines',
        'l10n_pe_catalog',
        'account_invoice_extras',
        'account_origin_invoice',
        'l10n_latam_invoice_document'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/account_invoice_correction_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 390.00,
}
