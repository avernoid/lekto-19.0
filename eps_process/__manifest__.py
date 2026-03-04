{
    'name': 'employee eps management',
    'version': '19.0.1.0.1',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'category': 'Payroll',
    'summary': 'This module allows you to manage the hiring process and eps control',
    'description': """
This module has been designed with the purpose of improving EPS management, in the module locating two fields, EPS credit and EPS management (management_eps).It also creates in the Employee module in the health area private information tab (hr.employee) at the bottom, a field called EPS (exists_eps) and EPS Policy (management_eps).Where the EPS policy field (management_eps) will be hidden as long as the boolean is not activated in the EPS field (exists_eps) and in the policy that the employee is registered from the employee file (hr.employee) it must also be reflected from the module location where the policies were created (management_eps).
""",
    'depends': [
        'hr_payroll',
        'personal_information',
        'various_data',
        'payroll_field',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/eps_credit_views.xml',
        'views/eps_management_views.xml',
        'views/hr_employee_relative_views.xml',
        'views/hr_employee_views.xml',
        'views/eps_process_menuitem.xml',
    ],
    'icon': '/eps_process/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 149.00,
    'module_type': 'official'
}
