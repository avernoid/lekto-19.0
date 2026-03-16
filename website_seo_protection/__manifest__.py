{
    'name': 'Website SEO Protection',
    'version': '18.0.1.0.5',
    'category': 'Website/Website',
    'summary': """Prevents crawler traps in dynamic Odoo website URLs. Block malicious bots and protect SEO.""",
    'description': """
Website SEO Protection
======================
Prevents Odoo appointment URLs from causing crawler traps that lead to server resource
exhaustion. Implements multi-layer HTTP-level protection:

- Layer 1: Returns HTTP 404 immediately for appointment ?domain= trap URLs (infinite crawl loop prevention).
- Layer 2: Adds X-Robots-Tag: noindex, nofollow to HTML responses for ?date= / ?datetime= calendar URLs.
- Fully supports Odoo multilingual URL prefixes (/en/, /es/, /pt_BR/, etc.).
- Zero configuration needed: install and it works automatically.
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'license': 'OPL-1',
    'depends': ['website'],
    'data': [],
    'icon': '/website_seo_protection/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 99.0,
    'module_type': 'official',
}
