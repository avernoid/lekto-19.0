{
    'name': ' Electronic Sales Record (PLE)',
    'icon': '/ple_sale_book/static/description/icon.svg',
    'version': '19.0.1.0.4',
    'author': 'Ganemo',
    'maintainer': 'Ganemo',
    'company': 'Ganemo',
    'website': 'https://www.ganemo.co',
    'category': 'Accounting',
    'summary': 'Submit your sales book to SUNAT through PLE.',
    'description': """
This module called “PLE reports” has been created to generate PLE sales reports for which it will contain an object called account.account.tag and will serve to position the information from the sales book in the columns.
It will contain these fields

- Field company_id “Company” of type many2one
- Field date_start “start date” of type date
- Field date_end “end date” of type date
- Field bool_consolidate_pos “Daily POS consolidation? of type boolean
- Field state_send “sending status” of type selection NOTE: This field must be activated when the next module is installed. SEE
- Field date_ple “Generated on” of type date.
- Field xls_binary “excel report” of type binary and this will contain information that will be explained later.
- Field txt_binary “report .TXT” of type binary and this will contain information that will be explained later.

The .txt, .xlsx files must be generated successfully
""",
    'depends': [
        'l10n_country_filter',
        'account_origin_invoice',
        'dua_in_invoice',
        'l10n_pe',
        'l10n_pe_reports',
    ],
    'data': [
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'data/ple_sale_tax_config_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_tags.xml',
        'data/ir_actions_server.xml',
        'views/account_account_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/ple_report_sale_views.xml',
        'views/res_company_views.xml',
        'views/uom_uom_views.xml',
        'views/ple_sale_tax_config_views.xml',
        'views/menu_ple_menus.xml',
        'views/ple_report_sale_menus.xml',
        'wizard/ple_update_tags_wizard_views.xml',
        'sql/get_tax.sql',
        'sql/validate_string.sql',
        'sql/validate_spaces.sql'
    ],
    'icon': '/ple_sale_book/static/description/icon.png',
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_combined_post_init_hook',
    'license': 'OPL-1',
    'module_type': 'official',
    'currency': 'USD',
    'price': 59.00
}
