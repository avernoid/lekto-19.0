import base64
import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.tools import get_lang
from ..reports.report_diary import DiaryReportExcel, DiaryReportTxt
from odoo.exceptions import ValidationError



class PleDiary(models.Model):
    _name = 'ple.report.diary'
    _description = 'Report PLE Registro Diario'
    _inherit = 'ple.report.base'
    _order = 'date_start desc, id desc'

    date_start = fields.Date(
        default=lambda self: (fields.Date.today().replace(day=1) - relativedelta(months=1)),
    )
    date_end = fields.Date(
        default=lambda self: (fields.Date.today().replace(day=1) - datetime.timedelta(days=1)),
    )

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start:
            self.date_end = self.date_start.replace(day=1) + relativedelta(months=1) - datetime.timedelta(days=1)

    state_send = fields.Selection(default='1')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_end < record.date_start:
                raise ValidationError(_('The end date cannot be earlier than the start date.'))

    xls_filename_diary = fields.Char()
    xls_binary_diary = fields.Binary(
        string='Excel Report - Journal',
        help='Complete Excel spreadsheet of the Electronic Journal for internal review and audit purposes.',
    )
    txt_filename_diary = fields.Char()
    txt_binary_diary = fields.Binary(
        string='TXT Report 5.1',
        help='Main Electronic Journal TXT file (PLE Book 5.1). Ready to upload to SUNAT\'s PLE application.',
    )
    txt_filename_diary1 = fields.Char()
    txt_binary_diary1 = fields.Binary(
        string='TXT Chart of Accounts with values 5.3',
        help='Chart of Accounts with transactional values (PLE Book 5.3). Lists all accounts used during the period with their codes, names, and group classification.',
    )
    txt_filename_diary2 = fields.Char()
    txt_binary_diary2 = fields.Binary(
        string='TXT Chart of Accounts without values 5.3',
        help='Chart of Accounts without transactional values (PLE Book 5.3). Account structure for reference.',
    )
    txt_filename_diary3 = fields.Char()
    txt_binary_diary3 = fields.Binary(
        string='TXT Report 5.2 Simplified Journal',
        help='Simplified Electronic Journal TXT file (PLE Book 5.2). For companies under the RER (Régimen Especial) regime.',
    )
    txt_filename_diary4 = fields.Char()
    txt_binary_diary4 = fields.Binary(
        string='TXT Chart of Accounts with values 5.4',
        help='Chart of Accounts with values (PLE Book 5.4). Companion to the simplified journal 5.2.',
    )
    txt_filename_diary5 = fields.Char()
    txt_binary_diary5 = fields.Binary(
        string='TXT Chart of Accounts without values 5.4',
        help='Chart of Accounts without values (PLE Book 5.4). Companion to the simplified journal 5.2.',
    )

    error_dialog_5_3 = fields.Text(
        string='Errors 5.3/5.4',
        readonly=True,
        help='Displays any errors or warnings encountered during the generation of PLE reports 5.3 and 5.4.',
    )


    def action_generate_excel(self):
        if not self.company_id.vat:
            raise ValidationError(
                'La compañía "%s" no tiene RUC/VAT configurado.\n'
                'Vaya a Ajustes → Compañías → %s y complete el campo "NIF/RUC" antes de generar el reporte PLE.'
                % (self.company_id.name, self.company_id.name)
            )

        query_aml = """
                SELECT
                TO_CHAR(account_move_line.date, 'YYYYMM00') as period_name,
                replace(replace(replace(account_move_line__move_id.name, '/', ''), '-', ''), ' ', '') as move_name,
                (SELECT get_journal_correlative(res_company.ple_type_contributor, account_move_line.ple_correlative)
                        FROM account_move
                        INNER JOIN res_company ON account_move.company_id = res_company.id
                        WHERE account_move.id = account_move_line__move_id.id LIMIT 1
                ) as correlative_line,
                coalesce(trim(replace(replace(replace(account_account.code_store->>%(active_company_root_id)s, '/', ''), '-', ''), '.', '')), '') as account_code,
                coalesce(res_currency.name, 'PEN') as currency_name,
                coalesce(l10n_latam_identification_type.l10n_pe_vat_code, '') as partner_document_type_code,
                coalesce(res_partner.vat, '') as partner_document_number,
                TO_CHAR(account_move_line__move_id.date, 'DD/MM/YYYY') as move_date,
                validate_string(string_ref(coalesce(coalesce(account_move_line__move_id.ref, account_move_line.name), '')), 200) as reference,
                string_ref(validate_string(coalesce(account_move_line.name, ''), 200)) as move_line_name,
                CASE
                  WHEN account_journal.type = 'sale' AND move_type IN ('out_invoice', 'out_refund') THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 1), '-', '0000'), LEFT(COALESCE(replace(split_part(replace(account_move_line.move_name, ' ', ''), '-', 1), '-', '0000'), ''), 4)), 4)
                  WHEN account_journal.type = 'purchase' AND move_type IN ('in_invoice', 'in_refund') THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 1), '-', '0000'), LEFT(COALESCE(replace(split_part(replace(account_move_line.ref, ' ', ''), '-', 1), '-', '0000'), ''), 4)), 4)
                  WHEN account_journal.type IN ('cash', 'bank', 'general') AND move_type = 'entry' THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 1), '-', '0000'), ''), 4)
                  ELSE '0000'
                END AS invoice_serie,
                CASE
                  WHEN account_journal.type = 'sale' AND move_type IN ('out_invoice', 'out_refund') THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 2), '-', '00000000'), LEFT(COALESCE(replace(split_part(replace(account_move_line.move_name, ' ', ''), '-', 2), '-', '00000000'), ''), 8) ), 8)
                  WHEN account_journal.type = 'purchase' AND move_type IN ('in_invoice', 'in_refund') THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 2), '-', '00000000'), LEFT(COALESCE(replace(split_part(replace(account_move_line.ref, ' ', ''), '-', 2), '-', '00000000'), ''), 8) ), 8)
                  WHEN account_journal.type IN ('cash', 'bank', 'general') AND move_type = 'entry' THEN
                    LEFT(COALESCE(replace(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 2), '-', '00000000'), ''), 8)
                  ELSE '00000000'
                END AS invoice_correlative,
                validate_string(COALESCE(split_part(replace(account_move_line__move_id.name, ' ', ''), '-', 1), '0000'),20) AS invoice_serie_oo,
                coalesce(left(split_part(replace(account_move_line__move_id.name, ' ', ''), '-', 2),20),'') AS invoice_correlative_oo,
                coalesce(TO_CHAR(account_move_line__move_id.invoice_date_due, 'DD/MM/YYYY'), '') as invoice_date_due,
                coalesce(l10n_latam_document_type.code, '00') AS invoice_document_type_code,
                account_move_line__move_id.move_type as move_type,
                account_move_line__move_id.ref as reference,
                account_move_line.name as ml_name,
                account_move_line.id as aml_id,
                to_json(account_move_line.analytic_distribution) as analytic_distribution2,
                account_move_line__move_id.name as ml_name2,
                account_move_line__move_id.payment_reference as payment_reference,
                account_move_line.debit as debit,
                account_move_line.credit as credit,
                CASE
                    WHEN
                        account_move_line__move_id.date <= '2023-09-30'
                    THEN
                        (
                            SELECT get_data_structured_diary(
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
                    ELSE ''
                END AS data_structured
                -- QUERIES TO MATCH MULTI TABLES
                FROM "account_move" as "account_move_line__move_id","account_move_line"
                --  TYPE JOIN   |  TABLE                        | MATCH
                    INNER JOIN  account_account                ON account_move_line.account_id = account_account.id
                    LEFT JOIN   res_currency                   ON account_move_line.currency_id = res_currency.id
                    LEFT JOIN   res_partner                    ON account_move_line.partner_id = res_partner.id
                    LEFT JOIN   account_journal                ON account_move_line.journal_id = account_journal.id
                    LEFT JOIN   l10n_latam_document_type       ON account_move_line.l10n_latam_document_type_id = l10n_latam_document_type.id
                    LEFT JOIN   l10n_latam_identification_type ON res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
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
            'company_id': self.company_id.id,
            'company_vat': self.company_id.vat or '',
            'date_start': self.date_start,
            'date_end': self.date_end,
            'state': 'posted',
            'active_company_root_id': str(self.env.company.root_id.id),
        }

        accounts = self.env['account.account'].search([('company_ids', 'in', self.company_id.id)])
        result_data = []

        for account in accounts:
            account_code = account.code.replace('.', '') if account.code else ''
            period_name = account.ple_date_account.strftime('%Y%m%d') if account.ple_date_account else ''
            account_name = account.name if account.name else ''
            name_group = account.group_id.name if account.group_id and account.group_id.name else ''
            code_prefix = self.company_id.code_prefix or ''
            state_account = account.ple_state_account or ''

            result_data.append({
                'period_name': period_name,
                'account_code': account_code,
                'account_name': account_name,
                'code_prefix': code_prefix,
                'name_group': name_group,
                'state_account': state_account,
            })
        result_data.sort(key=lambda x: x['account_code'])

        try:
            self.env.cr.execute(query_aml, params)
            data_aml = self.env.cr.dictfetchall()
            self.action_generate_report(data_aml, result_data)
        except Exception as error:
            raise ValidationError(f'Error al ejecutar la query, comunicarse con el administrador: \n {error}')

    def action_generate_report(self, data_aml, data_account):
        list_data = []
        analytic_accounts = {str(aa.id): aa.name for aa in self.env['account.analytic.account'].search([])}
        date_limit = datetime.date(2023,9,30)
        for obj_move_line in data_aml:
            ml_name = obj_move_line.get('ml_name', '') or obj_move_line.get('ml_name2', '')

            if obj_move_line.get('move_type') in ('entry', 'in_invoice', 'in_refund', 'in_receipt'):
                reference = obj_move_line.get('reference', '') or ml_name
            else:
                reference = obj_move_line.get('payment_reference', '') or ml_name

            move_name = obj_move_line.get('move_name', '')
            analytic_distribution = obj_move_line.get('analytic_distribution2', {})
            if isinstance(analytic_distribution, dict):
                nueva_lista = [
                    analytic_accounts[key]
                    for key in analytic_distribution.keys()
                    if key in analytic_accounts
                ]
            else:
                nueva_lista = []

            partner_document_type_code = obj_move_line.get('partner_document_type_code', '')
            partner_document_number = obj_move_line.get('partner_document_number', '')
            if len(partner_document_number) > 11:
                partner_document_number = partner_document_number[-11:]
            invoice_serie = obj_move_line.get('invoice_serie', '')
            invoice_correlative = obj_move_line.get('invoice_correlative', '')
            invoice_document_type_code = obj_move_line.get('invoice_document_type_code', '') if obj_move_line.get('invoice_document_type_code') else '00'

            data_structured = obj_move_line.get('data_structured', '') if self.date_end <= date_limit else f'{partner_document_number.zfill(11)}{invoice_document_type_code.zfill(2)}{invoice_serie.zfill(4)}{invoice_correlative.zfill(10)}'
            values_move = {
                'period_name': obj_move_line.get('period_name', ''),
                'move_name': move_name,
                'correlative_line': obj_move_line.get('correlative_line', ''),
                'account_code': obj_move_line.get('account_code', ''),
                'currency_name': obj_move_line.get('currency_name', ''),
                'analytic_distribution': ', '.join(nueva_lista),
                'partner_document_type_code': partner_document_type_code,
                'partner_document_number': obj_move_line.get('partner_document_number', ''),
                'move_date': obj_move_line.get('move_date', ''),
                'reference': reference.replace('\n', ' ')[:200],
                'move_line_name': ml_name.replace('\n', ' ')[:200],
                'invoice_serie': invoice_serie,
                'invoice_correlative': invoice_correlative,
                'invoice_date_due': obj_move_line.get('invoice_date_due', ''),
                'invoice_document_type_code': obj_move_line.get('invoice_document_type_code', ''),
                'debit': "{0:.2f}".format(obj_move_line.get('debit', '')),
                'credit': "{0:.2f}".format(obj_move_line.get('credit')),
                'data_structured': data_structured,
                'state': '1',
            }

            if values_move.get('invoice_document_type_code') == '':
                values_move.update({'invoice_document_type_code': '00'})

            if values_move.get('invoice_serie') == '':
                values_move.update({'invoice_serie': '00000000'})

            if values_move.get('invoice_correlative') == '':
                values_move.update({'invoice_correlative': '0000'})

            list_data.append(values_move)

        list_account = []
        for obj_account_line in data_account:
            values_account = {
                'period_name': obj_account_line.get('period_name', ''),
                'account_code': obj_account_line.get('account_code', ''),
                'account_name': obj_account_line.get('account_name', '')[:100],
                'code_prefix': obj_account_line.get('code_prefix', ''),
                'name_group': obj_account_line.get('name_group', '').replace('\n', '')[:60],
                'state_account': obj_account_line.get('state_account', ''),
            }
            list_account.append(values_account)

        diary_report = DiaryReportTxt(self, list_data, list_account)

        values_content = diary_report.get_content()
        report_values = {
            'txt_binary_diary': base64.b64encode(values_content and values_content.encode() or '\n'.encode()),
            'txt_filename_diary': diary_report.get_filename(),
            'txt_binary_diary3': base64.b64encode(values_content and values_content.encode() or '\n'.encode()),
            'txt_filename_diary3': diary_report.get_filename(3),
        }
        if not values_content:
            report_values['error_dialog'] = '- No hay contenido para presentar en el registro de libro diario 5.1 electrónico de este periodo. \n' \
                                            '- No hay contenido para presentar en el registro de libro diario 5.2 electrónico de este periodo. '
        else:
            report_values['error_dialog'] = ''

        values_content1 = diary_report.get_content(1)
        report_values.update({
            'txt_binary_diary1': base64.b64encode(values_content1 and values_content1.encode() or '\n'.encode()),
            'txt_filename_diary1': diary_report.get_filename(1),
            'txt_binary_diary4': base64.b64encode(values_content1 and values_content1.encode() or '\n'.encode()),
            'txt_filename_diary4': diary_report.get_filename(4),
        })

        if not values_content1:
            report_values['error_dialog_5_3'] = '- No hay contenido para presentar en el registro de libro diario 5.3 electrónico de este periodo. \n' \
                                                '- No hay contenido para presentar en el registro de libro diario 5.4 electrónico de este periodo.'
        else:
            report_values['error_dialog_5_3'] = ''

        values_content2 = diary_report.get_content(2)
        report_values.update({
            'txt_binary_diary2': base64.b64encode(values_content2 and values_content2.encode() or '\n'.encode()),
            'txt_filename_diary2': diary_report.get_filename(2),
            'txt_binary_diary5': base64.b64encode(values_content2 and values_content2.encode() or '\n'.encode()),
            'txt_filename_diary5': diary_report.get_filename(5)
        })

        diary_report_xls = DiaryReportExcel(self, list_data)
        values_content_xls = diary_report_xls.get_content()

        report_values.update({
            'xls_binary_diary': base64.b64encode(values_content_xls),
            'xls_filename_diary': diary_report_xls.get_filename(),
            'date_ple': fields.Date.today(),
            'state': 'load',
        })
        self.write(report_values)

    def action_close(self):
        super(PleDiary, self).action_close()

    def action_rollback(self):
        super(PleDiary, self).action_rollback()
        self.write({
            'xls_filename_diary': False,
            'xls_binary_diary': False,
            'txt_binary_diary': False,
            'txt_filename_diary': False,
            'txt_binary_diary1': False,
            'txt_filename_diary1': False,
            'txt_binary_diary2': False,
            'txt_filename_diary2': False,
            'txt_binary_diary3': False,
            'txt_filename_diary3': False,
            'txt_binary_diary4': False,
            'txt_filename_diary4': False,
            'txt_binary_diary5': False,
            'txt_filename_diary5': False,
        })
