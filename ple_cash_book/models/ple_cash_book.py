from odoo import api, fields, models
from ..reports.report_ple_bank import BankReport
from ..reports.report_ple_cash import CashReport
import base64
import re
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class PleCashBank(models.Model):
    _name = 'ple.report.cash.bank'
    _description = 'PLE Cash & Bank Book'
    _inherit = 'ple.report.base'
    _order = 'date_start desc, id desc'

    _date_range_valid = models.Constraint(
        'CHECK(date_end >= date_start)',
        'The end date must be equal to or after the start date.',
    )

    date_start = fields.Date(
        default=lambda self: fields.Date.today().replace(day=1) - relativedelta(months=1),
    )
    date_end = fields.Date(
        default=lambda self: fields.Date.today().replace(day=1) - relativedelta(days=1),
    )
    state_send = fields.Selection(default='1')

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start:
            self.date_end = self.date_start + relativedelta(months=1, day=1) - relativedelta(days=1)

    move_ids = fields.Many2many(
        comodel_name='account.move',
        string='Related Invoices',
        help="Journal entries included in this report. Populated automatically "
             "when the report is generated based on the selected date range.",
    )

    xls_filename_cash = fields.Char(
        string='Filename Excel - Cash',
        help="Auto-generated filename for the Cash Excel report.",
    )
    xls_binary_cash = fields.Binary(
        string='Excel Report - Cash',
        help="Downloadable Excel file containing Cash register data (TXT 1.1) "
             "for internal review and audit purposes.",
    )
    txt_filename_cash = fields.Char(
        string='Filename TXT - Cash',
        help="Auto-generated filename for the Cash TXT report.",
    )
    txt_binary_cash = fields.Binary(
        string='TXT Report - Cash',
        help="Downloadable TXT file in SUNAT PLE format for Cash entries (TXT 1.1). "
             "Upload this file directly to SUNAT's PLE program.",
    )

    xls_filename_bank = fields.Char(
        string='Filename Excel - Bank Accounts',
        help="Auto-generated filename for the Bank Accounts Excel report.",
    )
    xls_binary_bank = fields.Binary(
        string='Excel Report - Bank Accounts',
        help="Downloadable Excel file containing Bank Account register data (TXT 1.2) "
             "for internal review and audit purposes.",
    )
    txt_filename_bank = fields.Char(
        string='Filename TXT - Bank Accounts',
        help="Auto-generated filename for the Bank Accounts TXT report.",
    )
    txt_binary_bank = fields.Binary(
        string='TXT Report - Bank Accounts',
        help="Downloadable TXT file in SUNAT PLE format for Bank Account entries (TXT 1.2). "
             "Upload this file directly to SUNAT's PLE program.",
    )

    def action_generate_excel(self):
        query_cash = """
            SELECT
            coalesce(TO_CHAR(account_move_line.date, 'YYYYMM00'), '') as period,
            replace(replace(replace(account_move_line__move_id.name, '/', ''), '-', ''), ' ', '') as cuo,
            (SELECT
                CASE
                    WHEN company.ple_type_contributor = 'CUO' THEN
                        (SELECT COALESCE(ple_correlative, 'M000000001') FROM account_move_line WHERE move_id = account_move_line__move_id.id  LIMIT 1)
                    WHEN company.ple_type_contributor = 'RER' THEN 'M-RER'
                    ELSE ''
                END
            ) as correlative,
            coalesce(trim(replace(replace(replace(account_account.code_store->>%(active_company_root_id)s, '/', ''), '-', ''), '.', '')), '') as account_code,
            get_unit_operation_code(account_move_line__move_id.id) as unit_operation_code,
            '' as cost_center_code,
            coalesce(currency.name, 'PEN') as currency_name,
            (SELECT 
                CASE
                    WHEN account_move_line.serie_correlative IS NOT NULL THEN
                        SUBSTRING(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-',1),1,4)
                    ELSE '0000'
                END
            ) as serie,
            (SELECT 
                CASE
                    WHEN account_move_line.serie_correlative IS NOT NULL THEN
                        SUBSTRING(split_part(replace(account_move_line.serie_correlative, ' ', ''), '-', 2),1,8)
                    ELSE '00000000'
                END
            ) as document_number,
            coalesce(document_type.code, '00') AS type_payment_document,
            coalesce(TO_CHAR(account_move_line__move_id.date, 'DD/MM/YYYY'), '') as accounting_date,
            coalesce(TO_CHAR(account_move_line__move_id.invoice_date_due, 'DD/MM/YYYY'), '') as date_due,
            coalesce(TO_CHAR(account_move_line__move_id.date, 'DD/MM/YYYY'), '') as operation_date,
            (CASE WHEN account_move_line__move_id.ref IS NOT NULL THEN
                account_move_line__move_id.ref ELSE
                    SUBSTRING(account_move_line.name,1 ,200) END) as gloss,
            coalesce(account_move_line.name, '') as referential_gloss,
            UDF_numeric_char(account_move_line.debit) as debit, 
            UDF_numeric_char(account_move_line.credit) as credit,
            account_move_line.serie_correlative as id_group_sc,
            account_move_line.id as id_aml,
            data_structured_cash(account_move_line.serie_correlative) as data_structured_cash,
            account_move_line.full_reconcile_id as full_reconcile_id,
            account_move_line.ple_correlative as ple_correlative,
            account_move_line__move_id.name as am_name,
            TO_CHAR(account_move_line__move_id.date, 'YYYYMM00') as am_date,
            res_partner.country_id as country_partner,
            part.country_id as country_comp_partner, 
            account_journal.type as aj_type
            -- QUERIES TO MATCH MULTI TABLES
            FROM "account_move" as "account_move_line__move_id","account_move_line"
                LEFT JOIN   "account_account"                account_account       ON  account_move_line.account_id = account_account.id
                INNER JOIN  "res_currency"                   currency              ON  account_move_line.currency_id = currency.id
                INNER JOIN	"res_company"					 company			   ON  account_move_line.company_id = company.id
                LEFT JOIN   "l10n_latam_document_type"       document_type         ON  account_move_line.l10n_latam_document_type_id = document_type.id
                LEFT JOIN   res_partner                                            ON  account_move_line.partner_id = res_partner.id
                LEFT JOIN   account_journal                                        ON  account_move_line.journal_id = account_journal.id 
                LEFT JOIN   res_company                                            ON  account_move_line.company_id = res_company.id
                LEFT JOIN   res_partner as part                                    ON  res_company.partner_id = part.id
                LEFT JOIN   account_account_res_company_rel  account_companies     ON  account_account.id = account_companies.account_account_id
            WHERE
            ("account_move_line"."move_id"="account_move_line__move_id"."id") AND
                    ((((("account_move_line"."account_id" in (SELECT "account_account".id
                    FROM "account_account" WHERE "account_account"."ple_selection" = %(ple_selection)s
                    AND ("account_companies"."res_company_id" IS NULL OR
                    ("account_companies"."res_company_id" in (%(company_id)s)))
                    ORDER BY "account_account"."id"))  AND
                    ("account_move_line"."date" >= %(date_start)s))  AND
                    ("account_move_line"."date" <= %(date_end)s))  AND
                    ("account_move_line"."company_id" = %(company_id)s))  AND
                    ("account_move_line__move_id"."state" = %(state)s)) AND
                    ("account_move_line"."company_id" IS NULL   OR  ("account_move_line"."company_id" in (%(company_id)s)))
            ORDER BY "account_move_line"."date" DESC,"account_move_line"."move_name" DESC,"account_move_line"."id"
            """

        query_bank = """
            SELECT
            coalesce(TO_CHAR(account_move_line.date, 'YYYYMM00'), '') as period,
            replace(replace(replace(account_move_line__move_id.name, '/', ''), '-', ''), ' ', '') as cuo,
            (SELECT
                CASE
                    WHEN company.ple_type_contributor = 'CUO' THEN
                        (SELECT COALESCE(ple_correlative, 'M000000001') FROM account_move_line WHERE move_id = account_move_line__move_id.id  LIMIT 1)
                    WHEN company.ple_type_contributor = 'RER' THEN 'M-RER'
                    ELSE ''
                END
            ) as correlative,
            coalesce(res_bank.l10n_pe_edi_code, '') as bank_code,
            coalesce(res_partner_bank.acc_number, '') as account_bank_code,
            TO_CHAR(account_move_line.date, 'DD/MM/YYYY') as date,
            coalesce(account_move_line.name, '-') as operation_description,
            coalesce(payment_methods.code, '003') as payment_method,
            coalesce(identification_type.l10n_pe_vat_code, '-') as partner_type_document,
            coalesce(partner.vat, '-') as partner_document_number,
            coalesce(partner.name, 'VARIOS') as partner_name,
            (SELECT
                CASE
                    WHEN account_move_line__move_id.ref is not NULL THEN
                        validate_string(account_move_line__move_id.ref, 20)
                    WHEN account_move_line__move_id.name is not NULL THEN
                        validate_string(account_move_line__move_id.name, 20)
                    ELSE ''
                END
            ) as transaction_number,
            UDF_numeric_char(account_move_line.debit) as debit,     
            UDF_numeric_char(account_move_line.credit) as credit
            FROM "account_move" as "account_move_line__move_id","account_move_line"
                LEFT JOIN  "res_partner"                     partner               ON  account_move_line.partner_id = partner.id
                LEFT JOIN   "account_account"                account_account       ON  account_move_line.account_id = account_account.id
                INNER JOIN  "res_currency"                   currency              ON  account_move_line.currency_id = currency.id
                INNER JOIN	"res_company"					 company			   ON  account_move_line.company_id = company.id
                LEFT JOIN   "account_payment"                account_payment       ON  account_move_line.payment_id = account_payment.id
                LEFT JOIN   "payment_methods_codes"          payment_methods       ON  account_payment.means_payment_id = payment_methods.id
                LEFT JOIN   "res_partner_bank"               res_partner_bank      ON  account_account.bank_id = res_partner_bank.id
                LEFT JOIN   "res_bank"                       res_bank              ON  res_partner_bank.bank_id = res_bank.id
                LEFT JOIN   "l10n_latam_identification_type" identification_type   ON  partner.l10n_latam_identification_type_id = identification_type.id
                LEFT JOIN   account_account_res_company_rel  account_companies     ON  account_account.id = account_companies.account_account_id
            WHERE
            ("account_move_line"."move_id"="account_move_line__move_id"."id") AND
                    ((((("account_move_line"."account_id" in (SELECT "account_account".id
                    FROM "account_account" WHERE "account_account"."ple_selection" = %(ple_selection)s
                    AND ("account_companies"."res_company_id" IS NULL OR
                    ("account_companies"."res_company_id" in (%(company_id)s)))
                    ORDER BY "account_account"."id"))  AND
                    ("account_move_line"."date" >= %(date_start)s))  AND
                    ("account_move_line"."date" <= %(date_end)s))  AND
                    ("account_move_line"."company_id" = %(company_id)s))  AND
                    ("account_move_line__move_id"."state" = %(state)s)) AND
                    ("account_move_line"."company_id" IS NULL   OR  ("account_move_line"."company_id" in (%(company_id)s)))
            ORDER BY "account_move_line"."date" DESC,"account_move_line"."move_name" DESC,"account_move_line"."id"
            """

        cash_params = {
            'ple_selection': 'cash',
            'company_id': self.company_id.id,
            'date_start': str(self.date_start),
            'date_end': str(self.date_end),
            'state': 'posted',
            'active_company_root_id': str(self.env.company.root_id.id),
        }
        bank_params = {
            'ple_selection': 'bank',
            'company_id': self.company_id.id,
            'date_start': str(self.date_start),
            'date_end': str(self.date_end),
            'state': 'posted',
        }

        try:
            self.env.cr.execute(query_cash, cash_params)
            data_cash = self.env.cr.dictfetchall()
            self.env.cr.execute(query_bank, bank_params)
            data_bank = self.env.cr.dictfetchall()
            self.get_excel_data(data_cash, data_bank)
        except Exception as error:
            raise ValidationError(f'Error al ejecutar la query, comunicarse con el administrador: \n {error}')
        
    def get_excel_data(self, data_cash, data_bank):
        list_data_cash = []
        list_data_bank = []
        for obj_line_cash in data_cash:
            value_structured = ''
            if obj_line_cash['data_structured_cash']:
                data_structured = obj_line_cash['data_structured_cash'].split("**-**")
                namex = re.sub(r"[^a-zA-Z0-9]", "", data_structured[4])
                if data_structured[2] == 'sale' and data_structured[3] == 'F':
                    value_structured = '140100'
                if data_structured[2] == 'purchase' and data_structured[3] == 'F':
                    if data_structured[1] == 'F':
                        value_structured = '080100'
                    else:
                        value_structured = '080200'

                data_structured_cash = '{}&{}&{}&{}'.format(value_structured, data_structured[5], namex,
                                                   obj_line_cash['correlative'])
            else:
                data_structured_cash = ''

            cash_values = {
                'period': obj_line_cash.get('period', ''),
                'cuo': obj_line_cash.get('cuo', ''),
                'correlative': obj_line_cash.get('correlative', ''),
                'account_code': obj_line_cash.get('account_code', ''),
                'unit_operation_code': obj_line_cash.get('unit_operation_code', ''),
                'cost_center_code': obj_line_cash.get('cost_center_code', ''),
                'currency_name': obj_line_cash.get('currency_name', ''),
                'type_payment_document': obj_line_cash.get('type_payment_document', ''),
                'serie': obj_line_cash.get('serie', ''),
                'document_number': obj_line_cash.get('document_number', ''),
                'accounting_date': obj_line_cash.get('accounting_date', ''),
                'date_due': obj_line_cash.get('date_due', ''),
                'operation_date': obj_line_cash.get('operation_date', ''),
                'gloss': obj_line_cash.get('gloss', ''),
                'referential_gloss': obj_line_cash.get('referential_gloss', ''),
                'debit': obj_line_cash.get('debit', '0.00'),
                'credit': obj_line_cash.get('credit', '0.00'),
                'data_structured': data_structured_cash,
                'state': 1
            }
            list_data_cash.append(cash_values)

        for obj_line_bank in data_bank:
            transaction_type = obj_line_bank.get('transaction_type')
            if transaction_type:
                transaction_number = transaction_type
            else:
                name = obj_line_bank.get('transaction_number', '')
                name = re.sub(r"[^a-zA-Z0-9]", "", name)
                name = name.replace(' ', '').replace('\n', '').replace('\r', '')
                transaction_number = name

            bank_values = {
                'period': obj_line_bank.get('period', ''),
                'cuo': obj_line_bank.get('cuo', ''),
                'correlative': obj_line_bank.get('correlative', ''),
                'bank_code': obj_line_bank.get('bank_code', ''),
                'account_bank_code': obj_line_bank.get('account_bank_code', ''),
                'date': obj_line_bank.get('date', ''),
                'payment_method': obj_line_bank.get('payment_method', ''),
                'operation_description': obj_line_bank.get('operation_description', ''),
                'partner_type_document': obj_line_bank.get('partner_type_document', '-'),
                'partner_document_number': obj_line_bank.get('partner_document_number', '-'),
                'partner_name': obj_line_bank.get('partner_name', ''),
                'transaction_number': transaction_number,
                'debit': obj_line_bank.get('debit', '0.00'),
                'credit': obj_line_bank.get('credit', '0.00'),
                'state': 1
            }
            list_data_bank.append(bank_values)

        report_cash = CashReport(self, list_data_cash)
        cash_content = report_cash.get_content_txt()
        cash_content_xls = report_cash.get_content_excel()
        cash_filename_txt = report_cash.get_filename(file_type='txt')
        cash_filename_xlsx = report_cash.get_filename(file_type='xlsx')

        report_bank = BankReport(self, list_data_bank)
        bank_content = report_bank.get_content_txt()
        bank_content_xls = report_bank.get_content_excel()
        bank_filename_txt = report_bank.get_filename(file_type='txt')
        bank_filename_xlsx = report_bank.get_filename(file_type='xlsx')

        error_dialog = ''
        if not cash_content:
            error_dialog += '- No hay contenido en el registro "Detalle de los movimientos del efectivo" de este periodo.\n'
        if not bank_content:
            error_dialog += '- No hay contenido en el registro "Detalle de los movimientos de la cuenta corriente" de este periodo.'

        self.write({
            'txt_binary_cash': base64.b64encode(cash_content and cash_content.encode() or '\n'.encode()),
            'txt_filename_cash': cash_filename_txt,
            'xls_binary_cash': base64.b64encode(cash_content_xls),
            'xls_filename_cash': cash_filename_xlsx,
            'txt_binary_bank': base64.b64encode(bank_content and bank_content.encode() or '\n'.encode()),
            'txt_filename_bank': bank_filename_txt,
            'xls_binary_bank': base64.b64encode(bank_content_xls),
            'xls_filename_bank': bank_filename_xlsx,
            'error_dialog': error_dialog,
            'date_ple': fields.Date.today(),
            'state': 'load',
        })

    def action_close(self):
        super(PleCashBank, self).action_close()

    def action_rollback(self):
        super(PleCashBank, self).action_rollback()
        self.write({
            'txt_binary_cash': False,
            'txt_filename_cash': False,
            'xls_binary_cash': False,
            'xls_filename_cash': False,
            'txt_binary_bank': False,
            'txt_filename_bank': False,
            'xls_binary_bank': False,
            'xls_filename_bank': False,
        })
