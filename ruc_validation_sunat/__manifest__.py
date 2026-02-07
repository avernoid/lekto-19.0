{
    'name': 'RUC Validation SUNAT',
    'version': '19.0.1.0.1',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'This module creates a connection to the RUC query service.',
    'category': 'Accounting',
    'module_type': 'official',
    'depends': [
        'document_type_validation',
        'l10n_pe_catalog',
        'first_and_last_name'
    ],
    'data': [
        'views/partner_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 99.00,
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'icon': '/ruc_validation_sunat/static/description/icon.png',
    'images': ['static/description/banner.png'],
}
