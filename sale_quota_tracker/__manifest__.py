{
    'name': 'Sales Quota Tracker',
    'version': '19.0.1.0.7',
    'category': 'Sales/Sales',
    'summary': 'Manage monthly sales goals per salesperson by product and category',
    'description': """
        Sales Quota Tracker
        =========
        Allows Sales Managers to define monthly sales goals per salesperson,
        broken down by product and/or product category. Tracks both quantity
        and amount targets with automatic progress computation triggered
        by confirmed Sale Orders and validated Customer Invoices.

        Features:
        - Monthly goals per salesperson (unique constraint: one record per user/month/year)
        - Multiple goal lines: by product or by product category
        - Configurable source: Sale Orders or Customer Invoices (incl. Credit Notes)
        - Automatic recompute triggered on order confirmation/invoice validation
        - Manual "Update" button on form and bulk Server Action in list view
        - "Copy from previous month" shortcut for fast data entry
        - Role-based access: Managers edit all; Salespeople read only their own goals
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/sale_quota_tracker_security.xml',
        'security/ir.model.access.csv',
        'views/sale_quota_tracker_views.xml',
        'views/sale_quota_tracker_menus.xml',
    ],
    'icon': '/sale_quota_tracker/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 297.0,
    'module_type': 'official',
}
