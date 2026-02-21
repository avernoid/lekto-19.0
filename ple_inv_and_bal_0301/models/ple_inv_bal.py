import base64
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..reports.report_inv_bal import ReportInvBalExcel, ReportInvBalTxt


class PleInvBal(models.Model):
    _name = 'ple.report.inv.bal'
    _description = 'Statement of Financial Position'
    _inherit = 'ple.report.base'
    _order = 'date_start desc, id desc'

    _check_dates = models.Constraint(
        'CHECK(date_end >= date_start)',
        'The end date cannot be earlier than the start date.',
    )

    date_start = fields.Date(
        string='Start Date',
        default=lambda self: date(date.today().year - 1, 1, 1),
        help='Start date of the reporting period. Defaults to January 1st of the previous year. '
             'Changing this field will automatically update the End Date to December 31st of the same year.',
    )
    date_end = fields.Date(
        string='End Date',
        default=lambda self: date(date.today().year - 1, 12, 31),
        help='End date of the reporting period. Defaults to December 31st of the previous year. '
             'This field is auto-updated when Start Date changes, but can be manually adjusted. '
             'Must be equal to or later than Start Date.',
    )

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start:
            self.date_end = date(self.date_start.year, 12, 31)

    state_send = fields.Selection(
        string='Submission Status',
        default='1',
        help='Indicates whether this report is submitted by the entity itself or by a representative. '
             'Defaults to "Empresa o Entidad Operativa" (the company submits directly).',
    )

    line_ids = fields.One2many(
        comodel_name='ple.report.inv.bal.line',
        inverse_name='ple_report_inv_val_id',
        string='Report Lines',
        help='Detail lines of the balance sheet report, one per EEFF rubro. '
             'Generated automatically when clicking "Generate Report".',
    )
    financial_statements_catalog = fields.Selection(
        selection=[
            ('01', 'SUPERINTENDENCIA DEL MERCADO DE VALORES - SECTOR DIVERSAS - INDIVIDUAL'),
            ('02', 'SUPERINTENDENCIA DEL MERCADO DE VALORES - SECTOR SEGUROS - INDIVIDUAL'),
            ('03', 'SUPERINTENDENCIA DEL MERCADO DE VALORES - SECTOR BANCOS Y FINANCIERAS - INDIVIDUAL'),
            ('04', 'SUPERINTENDENCIA DEL MERCADO DE VALORES - ADMINISTRADORAS DE FONDOS DE PENSIONES (AFP)'),
            ('05', 'SUPERINTENDENCIA DEL MERCADO DE VALORES - AGENTES DE INTERMEDIACIÓN'),
            ('06', 'SUPERINTENDENCIA DEL MERCADO DE VALORES - FONDOS DE INVERSIÓN'),
            ('07', 'SUPERINTENDENCIA DEL MERCADO DE VALORES - PATRIMONIO EN FIDEICOMISOS'),
            ('08', 'SUPERINTENDENCIA DEL MERCADO DE VALORES - ICLV'),
            ('09', 'OTROS NO CONSIDERADOS EN LOS ANTERIORES')
        ],
        string='Financial Statements Catalog',
        default='09',
        required=True,
        help='SUNAT catalog code that identifies the type of financial statements being reported. '
             'Most companies should use "09 - OTROS NO CONSIDERADOS EN LOS ANTERIORES" unless they are '
             'supervised by the SMV (Superintendencia del Mercado de Valores).',
    )
    eeff_presentation_opportunity = fields.Selection(
        selection=[
            ('01', 'Al 31 de diciembre'),
            ('02', 'Al 31 de enero, por modificación del porcentaje'),
            ('03', 'Al 30 de junio, por modificación del coeficiente o porcentaje'),
            ('04',
             'Al último día del mes que sustentará la suspensión o modificación del coeficiente (distinto al 31 de enero o 30 de junio)'),
            ('05',
             'Al día anterior a la entrada en vigencia de la fusión, escisión y demás formas de reorganización de sociedades o emperesas o extinción '
             'de la persona jurídica'),
            ('06', 'A la fecha del balance de liquidación, cierre o cese definitivo del deudor tributario'),
            ('07', 'A la fecha de presentación para libre propósito')
        ],
        string='EEFF Presentation Opportunity',
        default='01',
        required=True,
        help='Specifies the occasion for submitting the financial statements to SUNAT. '
             'Most companies use "Al 31 de diciembre" for annual reporting. '
             'Other options apply for mid-year modifications, mergers, or liquidations.',
    )

    txt_filename = fields.Char(
        string='TXT Filename',
        help='Auto-generated filename for the TXT file in SUNAT PLE format.',
    )
    txt_binary = fields.Binary(
        string='TXT Report 3.1',
        help='The generated TXT file ready for uploading to the SUNAT PLE system.',
    )
    pdf_filename = fields.Char(
        string='PDF Filename',
        help='Auto-generated filename for the PDF report.',
    )
    pdf_binary = fields.Binary(
        string='PDF Report 3.1',
        help='The generated PDF report showing the Balance Sheet with Level 4 detail breakdown.',
    )

    def name_get(self):
        return [(obj.id, '{} - {}'.format(obj.date_start.strftime('%d/%m/%Y'), obj.date_end.strftime('%d/%m/%Y'))) for
                obj in self]
        

    def action_generate_report(self):
        self.line_ids.unlink()
        
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
            date_end=self.date_end,
            state='posted',
            financial_statements_catalog=self.financial_statements_catalog,
            date_self=self.date_end.strftime('%Y%m%d'),
            accounts=accounts,
            ple_report_inv_val_id=self.id,
            account_ids=account_ids
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
            self.env['ple.report.inv.bal.line'].create(lines_report)

        except Exception as error:
            raise ValidationError(f'Error al ejecutar la queries, comunicar al administrador: \n {error}')

    def check_key_in_dicts(self, key_val, list_data, new_data):
        if key_val not in list_data.keys():
            list_data.setdefault(key_val, new_data)
        else:
            new_credit = float(list_data[key_val]['credit']) + float(new_data['credit'])
            list_data[key_val]['credit'] = self.env['ple.report.base'].check_decimals(new_credit)

    def check_parent_lines(self, eeff_ple_id, credit, list_data):
        if isinstance(eeff_ple_id, int):
            eeff_ple_data = self.env['eeff.ple'].search([('id', '=', eeff_ple_id)])
        else:
            eeff_ple_data = eeff_ple_id
                        
        parent_ids = eeff_ple_data.parent_ids
        
        if not parent_ids:
            return
        else:
            for parent_id in parent_ids:
                parent_values = {
                    'sequence': parent_id.sequence,
                    'description': parent_id.description,
                    'name': self.date_end.strftime('%Y%m%d') or '',
                    'catalog_code': self.financial_statements_catalog,
                    'financial_state_code': parent_id.code or '',
                    'eeff_ple_id': parent_id.id or False,
                    'parent': parent_id.id or False,
                    'credit': credit,
                    'state': '1',
                    'ple_report_inv_val_id': self.id
                }
                self.check_key_in_dicts(parent_id.id, list_data, parent_values)
                self.check_parent_lines(parent_id, credit, list_data)

    def action_generate_excel(self):
        if self.action_generate_report():
            return
        list_data = []
        line_ids = self.env['ple.report.inv.bal.line'].search([('ple_report_inv_val_id', '=', self.id)],
                                                              order='sequence asc')
        for obj_line in line_ids:
            credit_temp = abs(float(obj_line.credit))
            real_credit = float(obj_line.credit)

            values = {
                'name': obj_line.name,
                'description': obj_line.description,
                'catalog_code': obj_line.catalog_code,
                'financial_state_code': obj_line.financial_state_code,
                'credit': round(credit_temp, 2),
                'state': obj_line.state,
                'sequence': obj_line.sequence,
                'eeff_ple_id': obj_line.eeff_ple_id,
                'account_ids': obj_line.account_ids,
                'real_credit': round(real_credit, 2),
            }
            list_data.append(values)

        report_txt = ReportInvBalTxt(self, list_data)
        report_xls = ReportInvBalExcel(self, list_data)

        values_content = report_txt.get_content()
        values_content_xls = report_xls.get_content()

        data = {
            'txt_binary': base64.b64encode(values_content.encode() or '\n'.encode()),
            'txt_filename': report_txt.get_filename(),
            'error_dialog': 'No hay contenido para presentar en el registro de ventas electrónicos de este periodo.' if not values_content else False,
            'xls_binary': base64.b64encode(values_content_xls),
            'xls_filename': report_xls.get_filename(),
            'date_ple': fields.Date.today(),
            'state': 'load'
        }
        self.write(data)

        for rec in self:
            report_name = "ple_inv_and_bal_0301.action_print_status_finance"
            pdf = self.env.ref(report_name)._render_qweb_pdf('ple_inv_and_bal_0301.print_status_finance', self.id)[0]
            rec.pdf_binary = base64.encodebytes(pdf)
            year, month, day = self.date_end.strftime('%Y/%m/%d').split('/')
            rec.pdf_filename = f'Libro_Estado de Situación Financiera_{year}{month}.pdf'

    def action_close(self):
        self.write({'state': 'closed'})

    def action_rollback(self):
        self.write({'state': 'draft'})
        self.write({
            'txt_binary': False,
            'txt_filename': False,
            'xls_binary': False,
            'xls_filename': False,
            'pdf_binary': False,
            'pdf_filename': False,
            'line_ids': False,
        })
