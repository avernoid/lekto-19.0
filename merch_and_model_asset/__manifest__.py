{
    'name': 'Merch and model assets',
    'version': '19.0.1.0.2',
    'category': 'Accounting/Accounting',
    'summary': "Track Brand, Model & Series specific data for your company assets easily.",
    'description': """
Merch & Model Assets
====================
This module extends the Odoo Assets functionality to include specific identification fields:
- Brand (Marca)
- Model (Modelo)
- Series (Serial/Plate)

These fields are essential for detailed asset tracking and inventory control within the accounting module.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'depends': ['account_asset'],
    'data': ['views/account_asset_views.xml'],
    'icon': '/merch_and_model_asset/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 20.0,
    'module_type': 'official'
}
