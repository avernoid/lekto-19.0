{
    'name': 'Project Task Photo Evidence',
    'version': '19.0.1.0.12',
    'category': 'Services/Project',
    'summary': 'Capture photo proof with geolocation for project tasks.',
    'description': """
        This module allows users to attach photo evidence to project tasks.
        It includes:
        - Geolocation capture (latitude/longitude)
        - Evidence requirements per product
        - Wizard for easy data entry
        - QWeb Report
    """,
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['project', 'sale_management', 'website', 'sale_project', 'portal_app_launcher'],
    'data': [
        'security/ir.model.access.csv',
        'data/portal_app_data.xml',
        'data/project_quick_reply_data.xml',
        'views/project_config_views.xml',
        'views/product_template_views.xml',
        'views/project_task_evidence_views.xml',
        'wizard/project_task_evidence_wizard_views.xml',
        'views/project_task_views.xml',
        'views/project_project_views.xml',

        'reports/project_task_evidence_report.xml',
        'reports/project_evidence_website_report.xml',
        'views/portal_evidence_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'project_task_photo_evidence/static/src/js/portal_evidence_filters.js',
            'project_task_photo_evidence/static/src/js/photo_evidence_portal.js',
        ],
        'web.assets_backend': [
            'project_task_photo_evidence/static/src/js/evidence_wizard_controller.js',
            'project_task_photo_evidence/static/src/xml/evidence_wizard.xml',
            'project_task_photo_evidence/static/src/js/image_camera_field.js',
            'project_task_photo_evidence/static/src/xml/image_camera_field.xml',
        ],
    },
    'icon': '/project_task_photo_evidence/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
    'currency': 'USD',
    'price': 297.0,
    'module_type': 'official',
}
