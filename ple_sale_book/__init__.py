from . import models
from . import reports
from . import wizard
from odoo import api, SUPERUSER_ID

def _combined_post_init_hook(env):
    _register_hook_account_report_sale_14(env)
    # _link_tags_ids(env) # Disabled in favor of manual Wizard configuration

def _register_hook_account_report_sale_14(env):
    
    existing_report = env['account.report'].search([('name', '=', 'VAT Report (RVIE Sales 14.4)')])
    existing_report_line = env['account.report.line'].search([('name', '=', 'RVIE 14.4')])

    if existing_report:
        additional_columns = [
            {
                'name': 'Asiento',
                'expression_label': 'move_name',
                'blank_if_zero': True,
            },
            {
                'name': 'Base Dscto IGV',
                'expression_label': 'base_igv_disc',
                'blank_if_zero': True,
            },
            {
                'name': 'Dscto IGV',
                'expression_label': 'tax_igv_disc',
                'blank_if_zero': True,
            },
            {
                'name': 'Otros Cargos',
                'expression_label': 'tax_other',
                'blank_if_zero': True,
            },
                
        ]
        existing_column_names = existing_report.column_ids.mapped('expression_label')
        columns_to_create = [
            col_data for col_data in additional_columns 
            if col_data['expression_label'] not in existing_column_names
        ]
        if columns_to_create:
            existing_report.write({
                'column_ids': [(0, 0, col_data) for col_data in columns_to_create]
            })
    if existing_report_line:
        existing_expression_labels = existing_report_line.expression_ids.mapped('label')
        if 'move_name' not in existing_expression_labels:
            existing_report_line.write({
                    'expression_ids': [(0, 0, {
                        'label': 'move_name',
                        'engine': 'custom',
                        'formula': '_report_custom_engine_ple_14_1',
                        'subformula': 'move_name',
                    })]
                })

def _link_tags_ids(env):
    env['account.tax']._link_tags_ids_update()
