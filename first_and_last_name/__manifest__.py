{
    'name': 'First and Last Name Details',
    'version': '19.0.1.0.2',
    'category': 'Extra Tools',
    'summary': """Desegregates contact names into first name, paternal surname, and maternal surname for legal compliance.""",
    'description': """This module adds three new fields to the contact form: First Name, Paternal Surname, and Maternal Surname. 
    It ensures structured data management specifically for individual contacts, assisting with legal and fiscal 
    identification requirements without altering Odoo's native display name logic. 
    Key features: 
    - Smart visibility: Fields hide automatically for company contacts. 
    - Native design: Integrated using Odoo's address format styles. 
    - Independent storage: Detail fields remain separate from the core 'Name' field.""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['base'],
    'data': ['views/partner_views.xml'],
    'assets': {
        'web.assets_tests': [
            'first_and_last_name/static/tests/tours/name_details_tour.js',
        ],
    },
    'icon': '/first_and_last_name/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 40.0,
    'module_type': 'official'
}
