{
    'name': 'Account Invoice Extras',
    'version': '19.0.1.0.0',
    'author': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'summary': 'Unified module for extra invoice fields and settings.',
    'description': '''
    Consolidates functionality from carrier_reference_number_invoice, print_aditional_comment, and aditional_document_reference.
    
    Features:
    - Adds "Guía(s) de Remisión" (carrier_ref_number) to invoices.
    - Adds "Otro tipo de documento" (aditional_document_reference) to invoices.
    - Adds company-level configuration "Información adicional factura impresa" (additional_information) printed on invoices.
    ''',
    'category': 'Accounting',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
        'views/res_company_views.xml',
        'reports/report_invoice_document.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'Other proprietary',
}
