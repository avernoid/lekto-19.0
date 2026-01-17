{
    'name': 'Document Type Validation',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'category': 'Localization/Localization',
    'summary': 'Manage validations for any location',
    'description': """
This Module manages and relates the type of document required by SUNAT (DNI, RUC, others) inherited object 'l10n_latam.identification.type'. Additionally, add validation, when saving a 'res.partner', and when making a change to the 'vat' field , or 'document_type_id' of 'res.partner', which does not meet the conditions of the parameters in the new fields created above.

Key Features:
- Custom Regex validation per document type.
- Exact or Maximum length validation.
- Numeric vs Alfanumeric validation.
    """,
    'depends': [
        'l10n_latam_base'
    ],
    'data': [
        'views/l10n_latam_identification_type_views.xml',
        'views/res_partner_views.xml'
    ],
    'assets': {},
    'icon': '/document_type_validation/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 20.00,
    'module_type': 'official',
}
