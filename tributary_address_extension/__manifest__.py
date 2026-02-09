{
    'name': 'Tributary Address Extension',
    'version': '19.0.0.0.1',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
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
    'icon': '/tributary_address_extension/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 20.00,
    'module_type': 'official',
}
