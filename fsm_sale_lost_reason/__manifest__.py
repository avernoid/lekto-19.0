{
    'name': 'FSM Sale Lost Reason',
    'version': '19.0.1.0.3',
    'category': 'Services/Field Service',
    'summary': 'Require lost reason for FSM tasks when no sale is made',
    'description': """
        This module adds a requirement to specify a lost reason when marking a Field Service task as done,
        if the project is configured to use lost reasons and no sales order has been confirmed.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['project', 'sale', 'sale_lost_reason', 'industry_fsm_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'wizard/project_task_lost_reason_wizard_views.xml',
    ],
    'i18n': ['i18n/es.po'],
    'images': ['static/description/banner.png'],
    'icon': '/fsm_sale_lost_reason/static/description/icon.png',
    'license': 'OPL-1',
    'tests': ['tests/test_fsm_lost_reason.py'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 65.0,
    'module_type': 'official'
}
