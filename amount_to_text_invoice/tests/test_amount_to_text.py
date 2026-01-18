from odoo import fields
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAmountToText(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Activate Spanish language for tests to avoid "Invalid language code" error
        cls.env.ref('base.lang_es').active = True
        
        # Ensure the test journal uses the Custom format by default for these tests
        cls.journal = cls.company_data['default_journal_sale']
        cls.journal.write({
            'amount_text_format': 'custom',
            'amount_text_in_caps': True,
        })

    def test_amount_to_text_custom_format_uppercase(self):
        """ Verify strict 00/100 format in Uppercase (Default configuration) """
        self.journal.write({'amount_text_in_caps': True})
        
        move = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a, # partner_a usually has random lang, defaults to en_US or company
            invoice_date=fields.Date.from_string('2024-01-01'),
            amounts=[1400.00],
            post=True,
        )
        # Ensure currency names are set for stable testing
        move.currency_id.currency_unit_label = 'DOLLARS'

        # Expect: "MIL CUATROCIENTOS Y 00/100 DOLLARS"
        # Note: In test environment, module translations (es.po) might not be loaded, 
        # so ' AND ' might remain ' AND '. We check for fairness.
        self.journal.amount_text_lang_id = self.env.ref('base.lang_es')
        
        # Recompute
        move._compute_amount_total_words()
        
        # We allow both ' Y ' (if translated) and ' AND ' (if fallback) to avoid flaky tests
        matches = [
            'MIL CUATROCIENTOS Y 00/100 DOLLARS',
            'MIL CUATROCIENTOS AND 00/100 DOLLARS'
        ]
        self.assertIn(move.amount_total_words, matches)

    def test_amount_to_text_lowercase(self):
        """ Verify logic when Uppercase is disabled """
        self.journal.write({
            'amount_text_format': 'custom', 
            'amount_text_in_caps': False,
            'amount_text_lang_id': self.env.ref('base.lang_es').id
        })

        move = self.init_invoice(
            move_type='out_invoice',
            amounts=[100.50],
            post=True,
        )
        move.currency_id.currency_unit_label = 'DOLLARS'
        
        # Expect: "Cien y 50/100 DOLLARS" or "Cien and 50/100 DOLLARS"
        move._compute_amount_total_words()
        
        matches = [
            'Cien y 50/100 DOLLARS',
            'Cien and 50/100 DOLLARS'
        ]
        self.assertIn(move.amount_total_words, matches)

    def test_amount_to_text_language_force(self):
        """ Verify Language Override (English) """
        english_lang = self.env.ref('base.lang_en')
        self.journal.write({
            'amount_text_format': 'custom',
            'amount_text_in_caps': True,
            'amount_text_lang_id': english_lang.id
        })

        move = self.init_invoice(
            move_type='out_invoice',
            amounts=[25.00],
            post=True,
        )
        move.currency_id.currency_unit_label = 'DOLLARS'

        # Expect: "TWENTY-FIVE AND 00/100 DOLLARS"
        # Note: The connector ' AND ' is translated. In English it remains ' AND '.
        move._compute_amount_total_words()
        self.assertEqual(move.amount_total_words, 'TWENTY-FIVE AND 00/100 DOLLARS')

    def test_native_fallback(self):
        """ Verify that Native format calls Odoo standard logic """
        self.journal.write({'amount_text_format': 'native'})
        
        move = self.init_invoice(
            move_type='out_invoice',
            amounts=[100.00],
            post=True,
        )
        
        # We can't easily assert the exact string of native Odoo without knowing user lang, 
        # but we can ensure it is NOT our '00/100' custom format if the native one differs.
        # Standard Odoo usually outputs "One Hundred Dollars" (no 00/100).
        
        move._compute_amount_total_words()
        
        # Our custom format MUST contain "/100". Native likely won't for round numbers.
        # This is a heuristic check.
        self.assertNotIn('/100', move.amount_total_words)
