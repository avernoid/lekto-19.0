{
    'name': 'Github Connector',
    'version': '18.0.1.0.7',
    'category': 'Developer Tools',
    'summary': 'Synchronize GitHub Organizations, Repositories, and Teams with Odoo.',
    'description': """
This module allows you to synchronize your GitHub account with Odoo.
It fetches Organizations, Repositories, Branches, and Teams.
Features:
- Mass Repository Sync with optimization for large accounts.
- Team and Member synchronization.
- Configurable sync limits to prevent timeouts.
- Scheduled actions for automatic updates.
""",
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'depends': ['base_setup', 'web'],
    'post_init_hook': 'post_init_hook',
    'data': [
        "security/ir_model_category.xml",
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "wizards/view_wizard_load_github_model.xml",
        "wizards/view_wizard_create_team.xml",
        "wizards/view_wizard_create_repository.xml",
        "wizards/view_wizard_invite_member_to_org.xml",
        "wizards/view_wizard_add_member_repo_to_team.xml",
        "views/view_reporting.xml",
        "views/view_github_team_partner.xml",
        "views/view_github_team_repository.xml",
        "views/action.xml",
        "views/view_res_partner.xml",
        "views/view_res_config_settings.xml",
        "views/view_github_analysis_rule.xml",
        "views/view_github_analysis_rule_group.xml",
        "views/view_github_organization.xml",
        "views/view_github_repository.xml",
        "views/view_github_repository_branch.xml",
        "views/view_github_team.xml",
        "views/menu.xml",
        "report/github_repository_branch_rule_info_report_view.xml",
    ],
    'external_dependencies': {
        'python': ['GitPython', 'pygount', 'pathspec', 'PyGithub']
    },
    'icon': '/github_connector_api/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': True,
    'currency': 'USD',
    'price': 497.0,
}
