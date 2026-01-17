{
    'name': 'Catálogos SUNAT',
    'version': '19.0.1.0.2',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'live_test_url': 'https://www.ganemo.co/demo',
    'summary': 'Standardized SUNAT Catalogs for Odoo Peru Localization.',
    'description': """
Standardized SUNAT Catalogs for Odoo Peru Localization.
Includes Catalog 01, 06, 53, 54, 59 and more for Electronic Invoicing (Annex 8).
    """,
    'category': 'Accounting',
    'module_type': 'official',
    'depends': [
        'document_type_validation',
        'l10n_pe_localization_menu',
        'l10n_pe',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/charge_discount_codes_data.xml',
        'data/document_type_data.xml',
        'data/l10n_latam_document_type_data.xml',
        'data/classification_services_data.xml',
        'data/payment_methods_codes_data.xml',
        'views/account_views.xml',
        'views/charge_discount_codes_views.xml',
        'views/l10n_latam_identification_type_views.xml',
        'views/product_template_views.xml',
        'views/classification_services_views.xml',
        'views/payment_methods_codes_views.xml',
    ],
    'icon': '/l10n_pe_catalog/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 0.00
}
