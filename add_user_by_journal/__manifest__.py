{
    'name': 'Journal Access Control',
    'version': '19.0.1.0.37',
    'category': 'Accounting',
    'summary': 'Restrict journal access by User or Group. Supports Public/Private logic.',
    'description': """
        This module allows you to restrict the visibility and usage of accounting journals 
        to specific users. It enhances security in multi-user environments by ensuring 
        that cashiers and accounting staff only see relevant journals in their dashboard 
        and search views.
        
        Key Features:
        - Assign users to specific journals.
        - Filter Accounting Dashboard based on user assignments.
        - Strict record-level security (Record Rules) for Journal Entries and Invoices.
        - Dedicated search filter "My Journals".
        - Administrator bypass group for full visibility.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'account',
    ],
    'data': [
        'security/add_user_by_journal_res_group.xml',
        'security/add_user_by_journal_ir_rule.xml',
        'views/account_journal_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'icon': '/add_user_by_journal/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 199.0,
    'module_type': 'official',
}
