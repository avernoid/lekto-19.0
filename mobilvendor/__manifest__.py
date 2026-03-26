# -*- coding: utf-8 -*-
{
    'name': "Mobilvendor Integration",
    'version': '19.0.1.2.11',
    'category': 'Services',
    'summary': """Integration between Odoo and Mobilvendor by using Mobilvendor's API""",
    
    'description': """
This integration connects the external Mobilvendor API with Odoo to facilitate seamless 
synchronization of essential business data across multiple entities, including customers, 
users, inventory, invoices, and payments. The integration ensures that both Odoo and 
the external system remain in sync, improving operational efficiency and providing a 
unified view of business operations.
    """,

    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'license': 'OPL-1',

    'depends': [
        'base', 
        'account', 
        'stock', 
        'sale', 
        'hr', 
        'contacts'
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/cron_jobs.xml',
        'views/res_company_view.xml',
        'views/stock_location_view.xml',
        'views/account_move_view.xml',
        'views/mobilvendor_route_views.xml',
        'views/res_partner_view.xml',
        'views/hr_employee_view.xml',
        'views/stock_picking_view.xml',
        'views/account_payment_views.xml',
        'views/product_template_views.xml',
        'views/product_pricelist_views.xml',
        'wizard/mobilvendor_sync_customer_wizard_views.xml'
    ],

    'icon': '/mobilvendor/static/description/icon.png',
    'images': ['static/description/banner.png'],
    
    'installable': True,
    'auto_install': False,
    'application': True,
    
    'currency': 'USD',
    'price': 3149.00,
    'module_type': 'official'
}
