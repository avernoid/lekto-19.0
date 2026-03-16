{
    'name': 'Github Project Portal',
    "version": "18.0.1.0.6",
    'author': 'Ganemo',
    "module_type": "official",
    'website': 'https://www.ganemo.co',
    'category': 'Project',
    "summary": "Integrate Odoo Projects with GitHub. Automate GitFlow, Manage PRs, and Validate Modules directly from Odoo tasks.",
    "description": """
        Integrate Odoo Projects with GitHub. Automate GitFlow, Manage PRs, and Validate Modules directly from Odoo tasks.
    """,
    'depends': ['project', 'github_connector_api'],
    'data': [
        'security/ir.model.access.csv',
        'views/github_repository_branch_views.xml',
        'views/github_repository_module_views.xml',
        'views/github_repository_views.xml',
        'views/project_github_views.xml'
    ],
    'installable': True,
    'auto_install': False,
    "license": "OPL-1",
    "currency": "USD",
    "price": 279.00,
    'icon': '/github_project_portal/static/description/icon.png',
    'images': ['static/description/banner.png'],
}
