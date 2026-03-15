{
    'name': 'GitHub Sales Access',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Manage GitHub repository access for active subscriptions from Odoo.',
    'description': """
Link sale order lines containing the "GitHub Connector" product to GitHub
collaborator records. Track, sync, and audit which GitHub users have access
to which repositories — directly from Odoo subscriptions.

Features:
- Two-level architecture: github.sales.access (user/subscription) → github.sales.access.repo (per repository).
- Smart Button on sale orders to access GitHub user records.
- Menu under Sales > Subscriptions > GitHub Access.
- Manual sync/revoke buttons per user (all repos) or per individual repository.
- Fallback activity when GitHub API fails (seat limit, 403, etc.).
- Monthly cron to sync all active repo accesses.
- Weekly cron to detect orphan collaborators (GitHub user without active subscription).
- Discrepancy filters: active in GitHub but subscription expired; subscription active but no GitHub user.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'github_product_document',
        'sale',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/github_sales_access_views.xml',
        'views/sale_order_views.xml',
        'views/product_template_views.xml',
        'views/menu.xml',
    ],
    'icon': '/github_sales_access/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 118.0,
    'module_type': 'official',
}
