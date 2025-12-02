{
    'name': 'Flexible Invoice Policy',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Allow invoicing delivery-policy products as ordered quantities.',
    'description': """
Flexible Invoice Policy
=======================
This module allows sales orders with 'delivery' policy products to be invoiced 
as if they had 'order' policy, controlled by a permission-based boolean field.

Features:
- Permission-controlled flag to bypass delivery policy
- Automatic chatter tracking of changes
- Optional auto-cleanup after invoice creation
- Compatible with auto_invoice_on_delivery and sale_one_step_invoice
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['sale'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'icon': '/sale_flexible_invoice_policy/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 76.0,
    'module_type': 'official',
}
