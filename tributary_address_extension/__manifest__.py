{
    'name': 'Tributary Address Extension',
    'version': '19.0.0.0.1',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'category': 'Localization/Localization',
    'summary': 'Add the field "Establishment Annex" in contact',
    'description': """
This module will add the field "Establishment Annex" in the contact form.
This field will only be displayed if the set country for the company is Peru; otherwise, it won't appear.
This field is a dependency for many modules of the Peruvian localization such as electronic invoicing.
    """,
    'depends': [
        'base',
    ],
    'data': [
        'views/res_partner_views.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'Other proprietary',
    'module_type': 'official',
    'currency': 'USD',
    'price': 20.00
}
