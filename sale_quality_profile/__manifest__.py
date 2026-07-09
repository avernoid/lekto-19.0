{
    'name': 'Sale Quality Profiles',
    'version': '19.0.1.0.5',
    'category': 'Sales/Quality',
    'summary': 'Choose, per sale order, which quality control points apply to '
               'its manufacturing and delivery operations.',
    'description': """
Sale Quality Profiles
=====================

Lets you decide, from the sale order, which Quality Control Points apply to the
Manufacturing Orders and to the Delivery operations spawned by that order.

Because the required quality often depends on the customer and the price, this
module introduces reusable *Quality Profiles* (tiers) grouping quality control
points. A sale order can pick one profile for manufacturing and one for
delivery, independently.

Design principles:

- Non-invasive: quality checks are still created by native Odoo; this module
  only prunes/augments the result AFTER the native creation, so it stays
  resilient to Odoo internal changes.
- Only operations that belong to a sale order WITH a profile are affected;
  every other flow keeps the exact native behavior.
- Scope: control points measured per Operation and per Product. Per-quantity
  (move line) checks keep their native behavior.
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'sale_stock',
        'sale_mrp',
        'quality_control',
        'quality_mrp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/quality_profile_views.xml',
        'views/sale_order_views.xml',
    ],
    'demo': [
        'demo/quality_profile_demo.xml',
    ],
    'icon': '/sale_quality_profile/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 120.0,
    'module_type': 'official',
}
