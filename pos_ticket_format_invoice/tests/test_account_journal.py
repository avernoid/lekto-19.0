from odoo import fields
from odoo.tests import common

@common.tagged('post_install', '-at_install')
class TestAccountJournal(common.TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.account_journal = self.env['account.journal'].create({
            'name':'Prueba de Facturas de cliente',
            'code':'INV4',
            'type':'sale',
            'l10n_latam_use_documents':True,
            'address_point_emission':'Prueba Informacion Adicional'
        })
        
    def test_fields_account_journal(self):
        self.assertEqual(self.account_journal.name, 'Prueba de Facturas de cliente')
        self.assertEqual(self.account_journal.code, 'INV4')
        self.assertEqual(self.account_journal.type, 'sale')
        self.assertEqual(self.account_journal.l10n_latam_use_documents, True)
        self.assertEqual(self.account_journal.address_point_emission, 'Prueba Informacion Adicional')
    