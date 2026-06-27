# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Product Variant Archive Lock',
    'version': '19.0.1.0.4',
    'category': 'Sales',
    'summary': """Keep manually archived variants archived, and hide attribute values from the sales order grid.""",
    'description': """
Variant Archive Lock & Order Grid Value Hiding
==============================================

Two per-product controls to decide exactly which variants and which attribute
values are offered for sale, without losing data.

1. Variant archive lock
-----------------------

In standard Odoo, editing an attribute or attribute value on a product
regenerates the variant matrix and reactivates (active=True) every variant
whose combination is still valid -- including the ones you had archived by
hand. With the per-product option enabled, manually archived variants stay
archived after the combinations are regenerated. New combinations are still
created and activated normally.

2. Hide attribute values from the order grid
--------------------------------------------

A per-value flag (``Hide from order grid``) removes an attribute value from
the Order Grid (sales matrix) without archiving, deleting or recreating its
variants. The variants keep all their data, stock and history and remain
active; the value is only hidden from the grid, and the setting survives
later attribute edits.

Design
------

* Does not reimplement Odoo's variant generation nor the matrix builder: it
  extends ``_create_variant_ids`` and ``_get_template_matrix`` by calling
  ``super()`` (the latter via a context flag honored by a minimal
  ``_only_active`` override). Resilient against upgrades.
* Zero cost for products that do not enable the options.
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['product', 'sale_product_matrix'],
    'data': [
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'views/product_attribute_views.xml',
    ],
    'icon': '/product_variant_archive_lock/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 40.0,
    'module_type': 'official',
}
