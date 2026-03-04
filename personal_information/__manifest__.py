{
    'name': 'Employee Personal Information',
    'version': '19.0.1.2.0',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'category': 'Human Resources/Employees',
    'summary': 'Manage detailed family information and legal name breakdown.',
    'description': """
Employee Personal Information
=============================

This module enhances the Employee form by adding:
1. **Relatives Tab**: A dedicated tab to manage detailed family information (Spouse, Children, etc.).
2. **Legal Name Breakdown**: Separate fields for First Name, Paternal Lastname, and Maternal Lastname.
3. **Automated Synchronization**:
   - Updates standard `children`, `spouse_complete_name`, and `spouse_birthdate` fields automatically from the Relatives tab.
4. **Legal Name Generation**:
   - Configurable option to auto-generate the Employee's "Legal Name" from their First and Last names.
   - Auto-capitalization of names.

Compatible: Enterprise & Community.
    """,
    'depends': [
        'hr'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_employee_relative_relation_data.xml',
        'views/hr_employee_relative_views.xml',
        'views/hr_employee_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'icon': '/personal_information/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 71.00,
    'module_type': 'official',
}