{
    'name': 'Website Sale Module Dependency',
    'version': '18.0.1.3.2',
    'category': 'Website/Website',
    'summary': """Auto-add Odoo module dependencies to the eCommerce cart and display total price with dependencies.""",
    'description': """When a customer adds an Odoo module to their cart, this module automatically
adds all required dependencies as separate cart lines. The product catalog
and product page display the total price including all dependencies.
Dependencies are resolved recursively and protected against circular references.
Each dependency appears as an independent, removable line in the cart.
Variant-aware: the correct variant matching the customer's selection is added.
Prices displayed are pricelist, multi-currency, and tax-aware.
Backend: salespersons can one-click add all missing dependencies to quotations.""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'website_sale',
    ],
    'data': [
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_module_dependency/static/src/js/dependency_price.js',
        ],
    },
    'icon': '/website_sale_module_dependency/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 649.0,
    'module_type': 'official',
}

