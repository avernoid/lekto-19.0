{
    'name': 'Financial Statement Annexes',
    'version': '19.0.1.0.2',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.com',
    'summary': 'Accounts receivable and payable reports with cut-off date and aging reports.',
    'description': """
    Add the annexes menu in accounting reports, along with all the logic to allow accounts receivable and payable reports with cut-off date and aging reports
    """,
    'category': 'Accounting',
    'depends': ['add_reconcile_date'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_report_financial_views.xml',
        'views/financial_annex_report_line_views.xml',
    ],
    'icon': '/financial_statement_annexes/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'module_type': 'official',
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 120.00
}
