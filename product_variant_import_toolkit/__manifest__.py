{
    'name': 'Product Variant Import Toolkit',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Bulk-import product variants with External IDs on template and '
               'variant, claim existing combinations, price_extra and freeze.',
    'description': """
Product Variant Import Toolkit
==============================

Wraps Odoo 19's native variant import (`import_attribute_values` / "Product
Values") and fills the gaps the core leaves out. Every behaviour was validated
live against a 19.0 database before shipping.

Features
--------
* **External ID for template AND variant in a single file.** Native import only
  assigns the variant External ID (the template one needs a separate pass); this
  toolkit assigns both from one file (`id` + `template_id` columns).
* **Claim by combination.** If a variant for a combination already exists — even
  archived, even one Odoo auto-generated without an External ID — it is
  reactivated and bound to your External ID instead of failing on the
  `product_product_combination_unique` index.
* **price_extra per attribute value**, imported with `price_extra:<Attribute>`
  columns.
* **Freeze non-imported combinations** using native attribute exclusions (the
  correct, persistent mechanism), with an honest report of combinations that
  pairwise exclusions cannot isolate (3+ attributes).

File format
-----------
One CSV, columns (only `name` and `import_attribute_values` are required):

    id, template_id, name, import_attribute_values,
    default_code, barcode, standard_price, list_price, categ_id, is_storable,
    price_extra:Color, price_extra:Size, ...
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_variant_import_views.xml',
    ],
    'icon': '/product_variant_import_toolkit/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 149.0,
    'module_type': 'official',
}
