{
    'name': 'Various Data',
    'version': '19.0.1.0.4',
    'category': 'Payroll',
    'summary': 'Creates the tax data menu in location, where the models of Minimum Vital Remuneration, UIT, SIS, SCTR are created',
    'description': """
This module provides functionalities for the creation, updating, and monitoring of specific models related to Minimum Vital Remuneration, Unidad Impositiva Tributaria(UIT), Seguro Integral de Salud (SIS), and Seguro Complementario de Trabajo de Riesgo (SCTR).
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': [
        'l10n_pe_localization_menu',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/various_data_rmv_views.xml',
        'views/various_data_sctr_views.xml',
        'views/various_data_sis_views.xml',
        'views/various_data_uit_views.xml',
    ],
    'icon': '/various_data/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 30.0,
    'module_type': 'official'
}
