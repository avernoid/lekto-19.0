{
    'name': 'Project Spreadsheet Report',
    'version': '19.0.1.0.0',
    'category': 'Services/Project',
    'summary': 'Generate Spreadsheet reports for Projects',
    'description': """
This module allows generating dynamic Spreadsheet reports for Projects based on templates.
It adds a configuration in Partners and Project Tags to select the default template.
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': "https://www.ganemo.co",
    'depends': ['project', 'spreadsheet_edition'],
    'data': [
        'security/ir.model.access.csv',
        'views/project_spreadsheet_template_views.xml',
        'views/project_spreadsheet_views.xml',
        'views/res_partner_views.xml',
        'views/project_tags_views.xml',
        'views/project_project_views.xml',
    ],
    'assets': {
        'spreadsheet.o_spreadsheet': [
            'project_spreadsheet_report/static/src/js/project_spreadsheet_action.js',
            'project_spreadsheet_report/static/src/xml/project_spreadsheet_action.xml',
        ],
        'web.assets_backend': [
            'project_spreadsheet_report/static/src/js/project_spreadsheet_loader.js',
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
