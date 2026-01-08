import logging

from odoo.tests.common import TransactionCase
from datetime import date

_logger = logging.getLogger(__name__)


class TestSaleDocumentType(TransactionCase):

    def setUp(self):
        super(TestSaleDocumentType, self).setUp()
        today = date.today()
        self.wizard_report_model = self.env['wizard.report.financial']
        self.env.ref("base.main_company").partner_id.write({
            'vat': "20557912879",
        })
        # Check if l10n_pe is installed before trying to ref it
        doc_type_ref = self.env.ref('l10n_pe.document_type01', raise_if_not_found=False)
        if doc_type_ref:
            self.env.ref("base.main_company").partner_id.write({
                'l10n_latam_identification_type_id': doc_type_ref.id,
            })
        self.account = self.env["account.account"].create(
            {
                'name': 'Cuenta',
                'code': '123',
                'account_type': 'expense',
                'reconcile': True,
            }
        )


        self.journal = self.env['account.journal'].create({
            'name': 'Test Journal',
            'code': 'TJ',
            'type': 'general',
        })

        self.account_move =  self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal.id,
            'date': today,
            'line_ids': [
                (0, 0, {
                    'name': 'line_debit',
                    'account_id': self.account.id,
                }),
                (0, 0, {
                    'name': 'line_credit',
                    'account_id': self.account.id,
                }),
            ],
        })

        self.data_report = {
            'date_start': today,
            'date_end': today,
            'xls_filename': 'Archivo',
            'xls_binary': False,
            'account_ids': [self.account.id],
        }
    
    def test_generate_data(self):
        self.account_move.action_post()
        self.env['account.move.line'].flush_model()
        model_wizard = self.wizard_report_model.create(self.data_report)
        data = model_wizard.generate_data()
        self.assertTrue(data)
        _logger.info('------------Test Generate data------------')
