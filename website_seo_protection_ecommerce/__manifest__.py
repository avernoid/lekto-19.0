{
    'name': 'Website SEO Protection: eCommerce',
    'version': '18.0.1.0.0',
    'category': 'Website/eCommerce',
    'summary': """Verifies SEO crawler guard does not block eCommerce routes. Auto-installs with website_sale.""",
    'description': """
        Companion module for website_seo_protection that validates all critical eCommerce routes
        (shop, products, categories, cart, checkout, payment confirmation) are never inadvertently
        blocked by the SEO crawler protection guard. Auto-installs when both website_seo_protection
        and website_sale are present. Contains only automated test cases — no UI or new models.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['website_seo_protection', 'website_sale'],
    'data': [],
    'icon': '/website_seo_protection_ecommerce/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': True,
    'application': False,
    'currency': 'USD',
    'price': 0.0,
    'module_type': 'official',
}

