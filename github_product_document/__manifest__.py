{
    'name': 'GitHub Product Document',
    'version': '18.0.1.1.1',
    'category': 'Developer Tools',
    'summary': """Deliver Odoo module source code as downloadable ZIP files via product.document.""",
    'description': """Link product variants to GitHub repository branches and automatically generate
downloadable ZIP archives for customers using Odoo's native product.document system.
Includes smart staleness detection, background cron updates, and eCommerce delivery on sale confirmation.""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'github_connector_api',
        'sale',
    ],
    'data': [
        'views/product_product_views.xml',
        'data/cron.xml',
    ],
    'icon': '/github_product_document/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 249.0,
    'module_type': 'official',
}
