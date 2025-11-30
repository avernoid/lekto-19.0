{
    'name': 'Employee Spreadsheet Report',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Generate Spreadsheet reports for Employees',
    'description': """
This module allows generating dynamic Spreadsheet reports for Employees based on templates.
It adds a configuration in Employees and Job Positions to select the default template.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['hr', 'spreadsheet_edition'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_spreadsheet_template_views.xml',
        'views/hr_employee_spreadsheet_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_job_views.xml',
    ],
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'hr_employee_spreadsheet_report/static/src/js/hr_employee_spreadsheet_action.js',
            'hr_employee_spreadsheet_report/static/src/xml/hr_employee_spreadsheet_action.xml',
        ],
        'web.assets_backend': [
            'hr_employee_spreadsheet_report/static/src/js/hr_employee_spreadsheet_loader.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'icon': 'static/description/icon.png',
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 249.0,
    'module_type': 'official',
}
