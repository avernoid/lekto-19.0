{
    'name': 'Ganemo DevOps Access',
    'version': '19.0.1.0.3',
    'category': 'Technical',
    'summary': 'Creates an agent bot user with a generated API key for autonomous log inspection.',
    'description': """
        Ganemo DevOps Access
        ====================
        This module is part of the Ganemo DevOps infrastructure.

        It creates a dedicated bot user (agent@ganemo.co) during installation and
        generates an Odoo API key for that user. The key is stored in ir.config_parameter
        so that the Antigravity agent can retrieve it via JSON-RPC and then use it to
        authenticate against the Odoo 19 JSON-2 API to autonomously inspect ir.logging
        after a failed Odoo.SH deployment.

        ⚠️  FOR STAGING/TESTING ENVIRONMENTS ONLY.
        ⚠️  Do NOT install on production databases.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['base'],
    'data': [],
    'icon': '/ganemo_devops_access/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,  # Must be installed as part of the deploy scope — not triggered by deps
    'application': False,
    'currency': 'USD',
    'price': 4500.0,
    'module_type': 'official',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
