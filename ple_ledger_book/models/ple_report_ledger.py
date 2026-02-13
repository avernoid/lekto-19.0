import base64
import calendar
import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.tools.float_utils import float_round
from ..reports.report_ledger import LedgerReportExcel, LedgerReportTxt

from odoo.exceptions import ValidationError


class PleLedger(models.Model):
    _name = 'ple.report.ledger'
    _description = 'PLE Report - General Ledger'
    _inherit = 'ple.report.base'
    _order = 'date_start desc, id desc'

    date_start = fields.Date(
        default=lambda self: fields.Date.context_today(self).replace(day=1) - relativedelta(months=1),
    )
    date_end = fields.Date(
        default=lambda self: fields.Date.context_today(self).replace(day=1) - datetime.timedelta(days=1),
    )
    state_send = fields.Selection(default='1')

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start:
            last_day = calendar.monthrange(self.date_start.year, self.date_start.month)[1]
            self.date_end = self.date_start.replace(day=last_day)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_start > record.date_end:
                raise ValidationError('La fecha de inicio no puede ser posterior a la fecha de fin.')

    xls_filename_ledger = fields.Char()
    xls_binary_ledger = fields.Binary(
        string='Excel Report - General Ledger',
        help='Download the General Ledger report in Excel format (.xlsx) for internal review and audit purposes.',
    )
    txt_filename_ledger = fields.Char()
    txt_binary_ledger = fields.Binary(
        string='TXT Report',
        help='Download the TXT file ready to upload to SUNAT\'s PLE application. The filename follows SUNAT\'s naming convention.',
    )

    def action_generate_excel(self):
        query = """
                SELECT
                TO_CHAR(account_move_line.date, 'YYYYMM00') as period_name,
                replace(replace(replace(account_move_line__move_id.name, '/', ''), '-', ''), ' ', '') as move_name,
                (SELECT get_journal_correlative(res_company.ple_type_contributor, account_move_line.ple_correlative)
                        FROM account_move 
                        INNER JOIN res_company ON account_move.company_id = res_company.id
                        WHERE account_move.id = account_move_line__move_id.id LIMIT 1
                ) as correlative_line,
                coalesce(trim(replace(replace(replace(account_account.code_store->>'%(active_company_root_id)s', '/', ''), '-', ''), '.', '')), '') as account_code,
                coalesce(res_currency.name, 'PEN') as currency_name,
                coalesce(l10n_latam_identification_type.l10n_pe_vat_code, '') as partner_document_type_code,
                coalesce(res_partner.vat, '') as partner_document_number,
    
                CASE 
                  WHEN account_journal.type = 'sale' AND account_move_line__move_id.move_type IN ('out_invoice', 'out_refund') THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 1), '-', '0000'), LEFT(COALESCE(replace(split_part(replace(account_move_line.move_name, ' ', ''), '-', 1), '-', '0000'), ''), 4)), 4)
                  WHEN account_journal.type = 'purchase' AND account_move_line__move_id.move_type IN ('in_invoice', 'in_refund') THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 1), '-', '0000'), LEFT(COALESCE(replace(split_part(replace(account_move_line.ref, ' ', ''), '-', 1), '-', '0000'), ''), 4)), 4)
                  WHEN account_journal.type IN ('cash', 'bank', 'general') AND account_move_line__move_id.move_type = 'entry' THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 1), '-', '0000'), ''), 4)
                  ELSE '0000'
                END AS invoice_serie,   

                CASE 
                  WHEN account_journal.type = 'sale' AND account_move_line__move_id.move_type IN ('out_invoice', 'out_refund') THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 2), '-', '00000000'), LEFT(COALESCE(replace(split_part(replace(account_move_line.move_name, ' ', ''), '-', 2), '-', '00000000'), ''), 8) ), 8)
                  WHEN account_journal.type = 'purchase' AND account_move_line__move_id.move_type IN ('in_invoice', 'in_refund') THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 2), '-', '00000000'), LEFT(COALESCE(replace(split_part(replace(account_move_line.ref, ' ', ''), '-', 2), '-', '00000000'), ''), 8) ), 8)
                  WHEN account_journal.type IN ('cash', 'bank', 'general') AND account_move_line__move_id.move_type = 'entry' THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 2), '-', '00000000'), ''), 8)
                  ELSE '00000000'
                END AS invoice_correlative, 
    
                validate_string(COALESCE(split_part(replace(account_move_line__move_id.name, ' ', ''), '-', 1), '0000'),20) AS invoice_serie_oo,
                coalesce(left(split_part(replace(account_move_line__move_id.name, ' ', ''), '-', 2),20),'') AS invoice_correlative_oo,               
                coalesce(TO_CHAR(account_move_line.date, 'DD/MM/YYYY'), '') as ml_date,
                coalesce(TO_CHAR(account_move_line.date_maturity, 'DD/MM/YYYY'), '') as ml_date_due,
                coalesce(TO_CHAR(account_move_line.date, 'DD/MM/YYYY'), '') as ml_date_issue,
                coalesce(l10n_latam_document_type.code, '00') AS invoice_document_type_code,
                account_move_line__move_id.move_type as move_type,
                coalesce(account_move_line.name, '') as ml_name,
                coalesce(account_move_line__move_id.name, '') as ml_name2,
                coalesce(account_move_line__move_id.ref, '') as reference,
                coalesce(account_move_line__move_id.payment_reference, '') as payment_reference,
                account_move_line.debit as debit,
                account_move_line.credit as credit,
                to_json(account_move_line.analytic_distribution) as analytic_distribution,
                CASE 
                    WHEN 
                        account_move_line__move_id.date <= '2023-09-30'
                    THEN 
                        (
                            SELECT get_data_structured_ledger(
                                account_journal.type,
                                account_journal.ple_no_include,
                                account_move.is_nodomicilied, 
                                account_move.name, 
                                account_move.date
                            ) 
                            FROM account_move
                            LEFT JOIN account_journal ON account_move.journal_id = account_journal.id
                            WHERE account_move.id = account_move_line__move_id.id
                        )
                    ELSE
                        (
                            SELECT get_data_structured_sire(
                                account_journal.type, 
                                account_journal.ple_no_include, 
                                account_move.is_nodomicilied, 
                                account_move.name, 
                                account_move.ref,
                                %(company_vat)s, 
                                res_partner.vat,
                                coalesce(l10n_latam_document_type.code, '00')
                            ) 
                            FROM account_move
                            LEFT JOIN account_journal ON account_move.journal_id = account_journal.id
                            WHERE account_move.id = account_move_line__move_id.id
                        )
                END AS data_structured
                -- QUERIES TO MATCH MULTI TABLES
                FROM "account_move" as "account_move_line__move_id","account_move_line" 
                --  TYPE JOIN   |  TABLE                        | MATCH
                    INNER JOIN  account_account                ON      account_move_line.account_id = account_account.id
                    LEFT JOIN   res_currency                   ON      account_move_line.currency_id = res_currency.id
                    LEFT JOIN   res_partner                    ON      account_move_line.partner_id = res_partner.id
                    LEFT JOIN   account_journal                ON      account_move_line.journal_id = account_journal.id
                    LEFT JOIN   l10n_latam_document_type       ON      account_move_line.l10n_latam_document_type_id = l10n_latam_document_type.id
                    LEFT JOIN   l10n_latam_identification_type ON      res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
                -- FILTER QUERIES     
                WHERE ("account_move_line"."move_id"="account_move_line__move_id"."id") AND 
                        (((((("account_move_line"."date" >= %(date_start)s)  AND  
                        ("account_move_line"."date" <= %(date_end)s))  AND  
                        ("account_move_line"."company_id" = %(company_id)s))  AND  
                        "account_move_line"."move_id" IS NOT NULL)  AND  
                        ("account_move_line__move_id"."state" = %(state)s))  AND  
                        "account_move_line"."account_id" IS NOT NULL) AND 
                        ("account_move_line"."company_id" IS NULL   OR  
                        ("account_move_line"."company_id" in (%(company_id)s)))
                -- ORDER DATA
                ORDER BY "account_move_line"."date" DESC,"account_move_line"."move_name" DESC,"account_move_line"."id" 
        """

        params = {
            'ple_selection': 'cash',
            'company_id': self.company_id.id,
            'company_vat': self.company_id.vat or '',
            'date_start': self.date_start,
            'date_end': self.date_end,
            'state': 'posted',
            'active_company_root_id':self.env.company.root_id.id,
            'ple_report_cash_bank': self.id
        }

        if not self.company_id.vat:
            raise ValidationError(
                'La compañía "%s" no tiene RUC/VAT configurado.\n'
                'Vaya a Ajustes → Compañías → %s y complete el campo "NIF/RUC" antes de generar el reporte PLE.'
                % (self.company_id.name, self.company_id.name)
            )

        try:
            self.env.cr.execute(query, params)
            data_aml = self.env.cr.dictfetchall()
            self.action_generate_report(data_aml)

        except Exception as error:
            raise ValidationError(f'Error al ejecutar la query, comunicarse con el administrador: \n {error}')

    def action_generate_report(self, data_aml):

        list_data = []
        analytic_accounts = {str(aa.id): aa.name for aa in self.env['account.analytic.account'].search([])}
        date_limit = datetime.date(2023,9,30)
        for obj_move_line in data_aml:
            if obj_move_line.get('ml_name') == ' ' or obj_move_line.get('ml_name') == '' or not obj_move_line.get(
                    'ml_name'):
                ml_name = obj_move_line.get('ml_name2')
            else:
                ml_name = obj_move_line.get('ml_name')

            if obj_move_line.get('move_type') in ('entry', 'in_invoice', 'in_refund', 'in_receipt'):
                if obj_move_line.get('reference') == ' ' or not obj_move_line.get('reference'):
                    reference = obj_move_line.get('ml_name2')
                else:
                    reference = obj_move_line.get('reference')
            else:
                if obj_move_line.get('payment_reference') == ' ' or obj_move_line.get(
                        'payment_reference') == '' or not obj_move_line.get('payment_reference'):
                    reference = obj_move_line.get('ml_name2')
                else:
                    reference = obj_move_line.get('payment_reference')

            analytic_distribution = obj_move_line.get('analytic_distribution', {})
            if isinstance(analytic_distribution, dict):
                nueva_lista = [
                    analytic_accounts[key]
                    for key in analytic_distribution.keys()
                    if key in analytic_accounts
                ]
            else:
                nueva_lista = []

            data_structured = obj_move_line.get('data_structured', '') if self.date_end <= date_limit else ''

            values = {
                'period_name': obj_move_line.get('period_name', ''),
                'move_name': obj_move_line.get('move_name', ''),
                'correlative_line': obj_move_line.get('correlative_line', ''),
                'account_code': obj_move_line.get('account_code', ''),
                'unit_code': '',
                'analytic_distribution':', '.join(nueva_lista),
                'currency_name': obj_move_line.get('currency_name', ''),
                'partner_document_type_code': obj_move_line.get('partner_document_type_code', ''),
                'partner_document_number': obj_move_line.get('partner_document_number', ''),
                'invoice_document_type_code': obj_move_line.get('invoice_document_type_code', ''),
                'invoice_serie': obj_move_line.get('invoice_serie', ''),
                'invoice_correlative': obj_move_line.get('invoice_correlative', ''),
                'ml_date': obj_move_line.get('ml_date', ''),
                'ml_date_due': obj_move_line.get('ml_date_due', ''),
                'ml_date_issue': obj_move_line.get('ml_date_issue', ''),
                'ml_name': ml_name.replace('\n', ' ')[:200] if ml_name else '',
                'reference': reference.replace('\n', ' ')[:200] if reference else '',
                'debit': "{0:.2f}".format(obj_move_line.get('debit', '')),
                'credit': "{0:.2f}".format(obj_move_line.get('credit')),
                'data_structured': data_structured,
                'state': '1',
            }
            if values.get('invoice_document_type_code') == '':
                values.update({'invoice_document_type_code': '00'})

            if values.get('invoice_serie') == '':
                values.update({'invoice_serie': '0000'})

            if values.get('invoice_correlative') == '':
                values.update({'invoice_correlative': '00000000'})

            list_data.append(values)

        ledger_report = LedgerReportTxt(self, list_data)
        ledger_content = ledger_report.get_content()
        ledger_report_xls = LedgerReportExcel(self, list_data)
        ledger_content_xls = ledger_report_xls.get_content()

        data = {
            'txt_binary_ledger': base64.b64encode(ledger_content and ledger_content.encode() or '\n'.encode()),
            'txt_filename_ledger': ledger_report.get_filename(),
            'error_dialog': 'No hay contenido para presentar en el registro libro mayor electrónico de este periodo' if not ledger_content else '',
            'xls_binary_ledger': base64.b64encode(ledger_content_xls),
            'xls_filename_ledger': ledger_report_xls.get_filename(),
            'date_ple': fields.Date.today(),
            'state': 'load',
        }
        self.write(data)

    def action_close(self):
        super(PleLedger, self).action_close()

    def action_rollback(self):
        super(PleLedger, self).action_rollback()
        self.write({
            'xls_filename_ledger': False,
            'xls_binary_ledger': False,
            'txt_binary_ledger': False,
            'txt_filename_ledger': False,
        })
