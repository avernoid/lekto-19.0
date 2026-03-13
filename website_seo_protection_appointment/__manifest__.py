{
    'name': 'Website SEO Protection: Appointment',
    'version': '18.0.1.0.0',
    'category': 'Website/SEO',
    'summary': """Fixes appointment calendar crawler trap (auto-installs with website_appointment).""",
    'description': """
Website SEO Protection: Appointment
====================================
Companion module for website_seo_protection. Auto-installs alongside website_appointment
to provide multi-layer crawler trap protection for Odoo appointment URLs.

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
    'depends': ['website_seo_protection', 'website_appointment'],
    'data': [],
    'icon': '/website_seo_protection_appointment/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': True,
    'application': False,
    'currency': 'USD',
    'price': 0.0,
    'module_type': 'official',
}
