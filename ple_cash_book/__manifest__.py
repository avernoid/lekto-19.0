{
    'name': 'PLE Cash & Bank Book',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': """Generates the electronic Cash & Bank Register (Libro Caja y Bancos) in TXT format for SUNAT PLE compliance.""",
    'description': """Generates the electronic register of Cash and Banks in .txt file, ready to present to SUNAT via electronic book program (PLE - SUNAT).
    This is a mandatory e-book for companies that are required to keep complete accounting in Peru.
    Produces TXT 1.1 (Cash) and TXT 1.2 (Bank) reports with Excel companions.""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': [
        'ple_purchase_book',
        'invoice_type_document'
    ],
    'data': [
        'views/account_views.xml',
        'views/ple_cash_book_views.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'sql/data_structured_cash.sql',
        'sql/find_full_reconcile.sql',
        'sql/get_unit_operation_code.sql',
        'sql/UDF_numeric_char.sql'
    ],
    'icon': '/ple_cash_book/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 160.00,
    'module_type': 'official'
}
