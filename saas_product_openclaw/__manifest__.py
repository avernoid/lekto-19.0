{
    'name': 'SaaS Product: OpenClaw',
    'version': '19.0.1.0.1',
    'category': 'Services',
    'summary': """OpenClaw product definition for the Orquestio SaaS orchestrator.""",
    'description': """
        Declares the OpenClaw blueprint, plans, and sellable product templates
        as master data on top of the generic saas_orchestrator layer.

        This module is the canonical home for any OpenClaw-specific knowledge
        in Odoo. The generic saas_orchestrator module stays product-agnostic;
        each SaaS product that Orquestio operates should ship its own
        saas_product_<name> module with its blueprint and plans as data XML.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'saas_orchestrator',
    ],
    'data': [
        'data/openclaw_data.xml',
        'data/openclaw_operations.xml',
    ],
    'icon': '/saas_product_openclaw/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 1100.0,
    'module_type': 'official',
}
