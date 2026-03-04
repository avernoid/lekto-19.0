{
    'name': 'Voucher Sending',
    'version': '19.0.1.0.6',
    'category': 'Payroll',
    'summary': """Automatically send payslips to employees' emails with secure portal access and digital signature.""",
    'description': """
        Automate payslip distribution in Odoo HR Payroll. This module allows HR administrators to send payslips
        in bulk to employees via email with a single click. Each email includes a secure, tokenized link giving
        the employee access to a personal portal page where they can view and digitally sign their payslip.
        Includes automatic PDF generation if no attachment exists yet.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'hr_payroll',
        'portal',
        'mail',
        'web'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_inherit.xml',
        'data/mail_template_data.xml',
        'views/hr_views.xml',
        'static/src/xml/payslip_portal_template.xml',
    ],
    'icon': '/voucher_sending/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 275.0,
    'module_type': 'official'
}
