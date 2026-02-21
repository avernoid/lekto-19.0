from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PleInvBalInitial(models.Model):
    _inherit = 'ple.report.inv.bal'

    line_initial_ids = fields.One2many(
        comodel_name='ple.inv.bal.line.initial.balances',
        inverse_name='ple_report_inv_val_id',
        string='Líneas de saldos iniciales'
    )

    def action_generate_initial_balances(self):
        self.line_initial_ids.unlink()
        account_weefftype_ids = self.env['account.account'].search_read([
                    ('eeff_ple_id.eeff_type', '=', '3.1')
                ], ['id'])
        if not account_weefftype_ids:
            self.write({'error_dialog': 'No hay cuentas configuradas con tipo 3.1 ESF'})
            return True
        accounts = ', '.join(map(lambda account: str(account['id']), account_weefftype_ids))

        account_winitial_ids = self.env['account.account'].search_read([
            ('include_initial_balance', '=', True)
        ], ['id'])
        if not account_winitial_ids:
            self.write({'error_dialog': 'No hay cuentas con include_initial_balance'})
            return True
        account_ids = map(lambda account: str(account['id']), account_winitial_ids)
        account_ids = ', '.join(account_ids)
        
        query = """
        SELECT
                eeff_ple.sequence as sequence,
                '{date_self}' as name,
                '{financial_statements_catalog}' as catalog_code,
                eeff_ple.code as financial_state_code,
                eeff_ple.id as eeff_ple_id,
                eeff_ple.id as parent,
                eeff_ple.description as description,
                UDF_numeric_char(sum(account_move_line.balance)) as credit,
                {ple_report_inv_val_id} as ple_report_inv_val_id
            -- QUERIES TO MATCH MULTI TABLES
                FROM account_move_line 
            --  TYPE JOIN   |  TABLE                        | MATCH
                INNER JOIN    account_account               ON account_move_line.account_id = account_account.id
                INNER JOIN    eeff_ple                      ON eeff_ple.id = account_account.eeff_ple_id
            -- FILTER QUERIES 
                WHERE eeff_ple.eeff_type = '3.1' and 
                account_move_line.date <= '{date_end}' and ((account_move_line.date >= '{date_start}') OR 
                "account_move_line"."account_id" in ({account_ids}))
                and account_move_line.company_id = {company_id} and  ("account_move_line"."account_id" in ({accounts}))
                and account_move_line.parent_state = '{state}'
                GROUP BY
                    eeff_ple.sequence, eeff_ple.code, eeff_ple.id, eeff_ple, parent;
        """.format(
            company_id=self.company_id.id,
            date_start=self.date_start,
            date_end=self.date_end - relativedelta(years=1),
            state='posted',
            financial_statements_catalog=self.financial_statements_catalog,
            date_self=self.date_end.strftime('%Y%m%d'),
            accounts=accounts,
            ple_report_inv_val_id=self.id,
            account_ids = account_ids
        )
        
        try:
            self.env.cr.execute(query)
            values = self.env.cr.dictfetchall()

            for dict in values:
                dict.setdefault('state', '1')

            lines_data = {}
            for dict in values:
                self.check_key_in_dicts(dict['eeff_ple_id'], lines_data, dict)
                self.check_parent_lines(dict['parent'], dict['credit'], lines_data)

            lines_report = list(lines_data.values())

            for data in lines_report:
                if len(data) == 10:
                    del data['parent']
            self.env['ple.inv.bal.line.initial.balances'].create(lines_report)

        except Exception as error:
            raise ValidationError(f'Error al ejecutar la queries, comunicar al administrador: \n {error}')

    def action_generate_initial_balances_301(self):
        return self.action_generate_initial_balances()




