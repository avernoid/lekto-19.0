{
    'name': 'Auto Engineering ECO',
    'version': '19.0.1.0.1',
    'category': 'Manufacturing/PLM',
    'summary': 'Automatically create a PLM Engineering Change Order (ECO) and a draft BOM when confirming a sale of a made-to-order product.',
    'description': """
Auto Engineering ECO
====================

When a sale order is confirmed, this module inspects each order line and, for
every eligible product, automatically creates a PLM Engineering Change Order
(mrp.eco) together with a draft Bill of Materials, so engineering can define the
components inside the standard Odoo PLM flow.

A product is eligible when ALL of the following are true:

- Its product category is flagged "Requires custom engineering".
- It is a storable good (type='consu' and is_storable=True).
- It does not have an active Bill of Materials yet.

The ECO uses the ECO Type configured on the category, is placed in the first
stage by sequence, and is linked back to the originating sale order. The process
is idempotent (one ECO/BOM per unique product, never duplicated on
reconfirmation) and runs with elevated privileges, so salespeople without PLM
access still trigger it. Any failure is logged without blocking the sale.
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'sale_management',
        'mrp',
        'mrp_plm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_category_views.xml',
        'views/mrp_eco_views.xml',
        'views/sale_order_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'icon': '/sale_mrp_plm_auto_eco/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 69.0,
    'module_type': 'official',
}
