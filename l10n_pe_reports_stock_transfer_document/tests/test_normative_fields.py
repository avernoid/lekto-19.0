"""Normative corrections of the Kardex PLE (RS 108-2020, structures 12.1/13.1).

Column layout of a line, 0-indexed after ``split('|')``:
period(0) cuo(1) number(2) establishment(3) catalogue(4) type_of_existence(5)
default_code(6) catalogue_used(7) unspsc(8) date(9) document_type(10) ...
"""

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.l10n_pe_reports_stock.wizard.stock_move_ple_report import (
    L10n_PeStockPleWizard as NativeWizard,
)

from .common import PleBridgeCommon

CATALOGUE = 4
EXISTENCE_TYPE = 5
CODE = 6
CATALOGUE_USED = 7
UNSPSC = 8
DATE = 9


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPleNormativeFields(PleBridgeCommon):

    def _lines(self, content):
        return [line.split('|') for line in content.split('\n') if line]

    def _line_of(self, content, move):
        cuo = str(move.id).zfill(6)
        return next(cols for cols in self._lines(content) if cols[1] == cuo)

    def _receipt_move(self, purchase):
        return purchase.picking_ids.move_ids.filtered(
            lambda m: m.product_id == self.product)[:1]

    # ------------------------------------------------------------------
    # Field 5 -- the catalogue of the code in field 7
    # ------------------------------------------------------------------
    @freeze_time('2026-01-15')
    def test_field_5_defaults_to_others(self):
        """An internal reference is not a UNSPSC code: catalogue 9, not 1."""
        self._build_fixture()
        content = self._report()._get_ple_report_content('1301')
        lines = self._lines(content)
        self.assertTrue(lines)
        for columns in lines:
            self.assertEqual(columns[CATALOGUE], '9')

    @freeze_time('2026-01-15')
    def test_field_5_and_7_follow_the_configured_source(self):
        """Source barcode -> the code is the barcode and the catalogue is GTIN."""
        purchase, _sale = self._build_fixture()
        self.product.barcode = '7501234567890'
        template = self.product.product_tmpl_id
        template.l10n_pe_existence_code_source = 'barcode'
        self.assertEqual(template.l10n_pe_existence_catalogue, '3',
                         "the catalogue must be proposed from the source")

        columns = self._line_of(
            self._report()._get_ple_report_content('1301'),
            self._receipt_move(purchase))
        self.assertEqual(columns[CODE], '7501234567890')
        self.assertEqual(columns[CATALOGUE], '3')

    @freeze_time('2026-01-15')
    def test_declared_catalogue_survives_a_source_it_does_not_match(self):
        """A client whose internal reference *is* a GTIN declares catalogue 3."""
        purchase, _sale = self._build_fixture()
        template = self.product.product_tmpl_id
        template.l10n_pe_existence_catalogue = '3'

        columns = self._line_of(
            self._report()._get_ple_report_content('1301'),
            self._receipt_move(purchase))
        self.assertEqual(columns[CATALOGUE], '3')
        self.assertEqual(columns[CODE],
                         self.product._l10n_pe_ple_existence_code(),
                         "the code still comes from the internal reference")
        self.assertEqual(columns[CODE], 'FURN9999',
                         "and it is still scrubbed the way native does")

    @freeze_time('2026-01-15')
    def test_field_7_keeps_the_hyphen_and_strips_the_asterisk(self):
        """The scrub of v19.0.3.0.1 (task 69361), which the native one undoes.

        Native strips ``_ - / '``; this module must keep the hyphen (the
        client's own codes carry it) and strip the asterisk instead. Without
        this test the rule has nothing protecting it -- that is how it nearly
        got reverted.
        """
        purchase, _sale = self._build_fixture()
        self.product.default_code = 'IH-21114/A_1*B'

        columns = self._line_of(
            self._report()._get_ple_report_content('1301'),
            self._receipt_move(purchase))
        self.assertEqual(columns[CODE], 'IH-21114A1B')
        self.assertIn('-', columns[CODE], "the hyphen must survive")
        self.assertNotIn('*', columns[CODE], "the asterisk must not")

    # ------------------------------------------------------------------
    # Field 8 -- only declared when field 9 carries a code
    # ------------------------------------------------------------------
    @freeze_time('2026-01-15')
    def test_field_8_empty_without_unspsc(self):
        purchase, _sale = self._build_fixture()
        self.product.product_tmpl_id.unspsc_code_id = False

        columns = self._line_of(
            self._report()._get_ple_report_content('1301'),
            self._receipt_move(purchase))
        self.assertEqual(columns[UNSPSC], '')
        self.assertEqual(columns[CATALOGUE_USED], '',
                         "no code in field 9 -> field 8 must not declare a "
                         "catalogue")

    @freeze_time('2026-01-15')
    def test_field_8_declared_with_unspsc(self):
        code = self.env['product.unspsc.code'].search(
            [('applies_to', '=', 'product')], limit=1)
        if not code:
            self.skipTest("no UNSPSC code loaded")
        purchase, _sale = self._build_fixture()
        self.product.product_tmpl_id.unspsc_code_id = code.id

        columns = self._line_of(
            self._report()._get_ple_report_content('1301'),
            self._receipt_move(purchase))
        self.assertEqual(columns[UNSPSC], code.code)
        self.assertEqual(columns[CATALOGUE_USED], '1')

    # ------------------------------------------------------------------
    # Field 6 -- the opening rows read the product, like the movement rows
    # ------------------------------------------------------------------
    def test_opening_existence_type_comes_from_the_product(self):
        with freeze_time('2026-01-15'):
            self._build_fixture()
        self.product.product_tmpl_id.l10n_pe_type_of_existence = '1'
        self.product2.product_tmpl_id.l10n_pe_type_of_existence = False

        # A period after the movements: every line is an opening (A1) one.
        wizard = self.env['l10n_pe.stock.ple.wizard'].create({
            'date_from': '2026-02-01',
            'date_to': '2026-02-28',
        })
        for report in ('1301', '1201'):
            lines = self._lines(wizard._get_ple_report_content(report))
            openings = {cols[1]: cols for cols in lines if cols[2] == 'A1'}
            self.assertTrue(openings, "the period must be all openings")

            own = openings.get(f'{self.product.id}A1'.zfill(6))
            self.assertTrue(own, "the product must have an opening row")
            self.assertEqual(own[EXISTENCE_TYPE], '01',
                             "report %s: the opening must read the product" % report)

            other = openings.get(f'{self.product2.id}A1'.zfill(6))
            if other:
                self.assertEqual(other[EXISTENCE_TYPE], '99',
                                 "an unset type still falls back to 99")

    # ------------------------------------------------------------------
    # Field 10 -- never later than the period of field 1
    # ------------------------------------------------------------------
    @freeze_time('2026-01-15')
    def test_field_10_never_after_the_period(self):
        purchase, _sale = self._build_fixture()
        bill = purchase.invoice_ids
        bill.button_draft()
        bill.invoice_date = '2026-02-05'
        bill.action_post()

        wizard = self._report()
        move = self._receipt_move(purchase)
        columns = self._line_of(wizard._get_ple_report_content('1301'), move)
        self.assertEqual(columns[DATE], move.date.strftime('%d/%m/%Y'),
                         "a document dated after the period must fall back to "
                         "the movement date")

        # Guard: the native behaviour this corrects is really the other one.
        native = self._line_of(
            NativeWizard._get_ple_report_content(wizard, '1301'), move)
        self.assertEqual(native[DATE], '05/02/2026',
                         "native emits the out-of-period document date")

    @freeze_time('2026-01-15')
    def test_field_10_keeps_the_document_date_inside_the_period(self):
        purchase, _sale = self._build_fixture()
        wizard = self._report()
        move = self._receipt_move(purchase)
        columns = self._line_of(wizard._get_ple_report_content('1301'), move)
        native = self._line_of(
            NativeWizard._get_ple_report_content(wizard, '1301'), move)
        self.assertEqual(columns[DATE], native[DATE],
                         "inside the period the native date must stand")

    # ------------------------------------------------------------------
    # Field 10 -- the date of the document THIS ROW reports
    #
    # Production (Huarcaya, 2026, 236.107 movements with a captured document):
    # 14.005 rows report a document of one type and a date of another, 13.995
    # of them a credit note dated by its own invoice; 163 take the date from an
    # unposted document.
    # ------------------------------------------------------------------
    def _return_with_credit_note(self):
        """Receipt + bill, then a return whose line also carries a credit note.

        The credit note is created AFTER the bill, so it has the higher id --
        which is what makes the native ``sorted('id')[:1]`` pick the bill and
        print its date next to the credit note's number.
        """
        purchase, _sale = self._build_fixture()
        bill = purchase.invoice_ids
        picking = purchase.picking_ids.filtered(lambda p: p.state == 'done')[:1]
        wiz = self.env['stock.return.picking'].with_context(
            active_id=picking.id, active_model='stock.picking').create({})
        for line in wiz.product_return_moves:
            line.quantity = line.move_id.quantity
        return_picking = self.env['stock.picking'].browse(
            wiz.action_create_returns()['res_id'])
        return_picking.move_line_ids.write({'picked': True})
        for ml in return_picking.move_line_ids:
            ml.quantity = ml.move_id.product_uom_qty
        return_picking.button_validate()

        refund = bill._reverse_moves([{
            'invoice_date': '2026-01-20',
            'l10n_latam_document_type_id': self.doc_type_07.id,
            'l10n_latam_document_number': 'FC01-00000321',
        }])
        refund.action_post()
        ret_move = return_picking.move_ids.filtered(
            lambda m: m.product_id == self.product)[:1]
        # Taken from the receipt picking explicitly: ``_receipt_move`` walks
        # ``purchase.picking_ids``, which now also holds the return picking and
        # would hand back the return move instead.
        receipt_move = picking.move_ids.filtered(
            lambda m: m.product_id == self.product)[:1]
        return purchase, bill, refund, ret_move, receipt_move

    @freeze_time('2026-01-25')
    def test_field_10_takes_the_date_of_the_document_it_reports(self):
        """A return reporting its credit note must carry the CREDIT NOTE's date."""
        _purchase, bill, refund, ret_move, _receipt = self._return_with_credit_note()
        self.assertEqual(ret_move.transfer_document_type_id, self.doc_type_07,
                         "precondition: the row reports the credit note")
        self.assertNotEqual(bill.invoice_date, refund.invoice_date,
                            "precondition: the two dates differ")

        wizard = self._report()
        columns = self._line_of(wizard._get_ple_report_content('1301'), ret_move)
        self.assertEqual(columns[DATE], refund.invoice_date.strftime('%d/%m/%Y'))

        # Guard: this really is the native behaviour being corrected.
        native = self._line_of(
            NativeWizard._get_ple_report_content(wizard, '1301'), ret_move)
        self.assertEqual(native[DATE], bill.invoice_date.strftime('%d/%m/%Y'),
                         "native dates the credit note with its bill")

    @freeze_time('2026-01-25')
    def test_field_10_left_native_when_the_capture_disagrees(self):
        """The gate: a stored document the derivation does not confirm.

        This is the shape of the 12.268 sealed movements whose stored credit
        note is itself the legacy error.  Propagating ITS date would only
        spread a document already known to be wrong, so the native date stands
        until they are reprocessed.
        """
        _purchase, bill, refund, _ret, receipt = self._return_with_credit_note()
        # The receipt is NOT a return, so the derivation resolves it to the
        # bill; stamping a credit note on it is a stored value the derivation
        # does not confirm -- the shape of the sealed legacy movements.
        receipt.write({
            'transfer_document_type_id': self.doc_type_07.id,
            'serie_transfer_document': 'FC01',
            'number_transfer_document': '00000321',
        })
        self.assertEqual(receipt._itde_source_invoice(), bill,
                         "precondition: the derivation says bill, not refund")

        wizard = self._report()
        columns = self._line_of(wizard._get_ple_report_content('1301'), receipt)
        self.assertEqual(columns[DATE], bill.invoice_date.strftime('%d/%m/%Y'),
                         "the unconfirmed credit note must not date the row")
        self.assertNotEqual(columns[DATE],
                            refund.invoice_date.strftime('%d/%m/%Y'))

    @freeze_time('2026-01-25')
    def test_field_10_ignores_an_unposted_document(self):
        """Field 10 is the ISSUE date; a draft has not been issued."""
        purchase, _sale = self._build_fixture()
        bill = purchase.invoice_ids
        bill.button_draft()
        move = self._receipt_move(purchase)

        wizard = self._report()
        columns = self._line_of(wizard._get_ple_report_content('1301'), move)
        self.assertEqual(columns[DATE], move.date.strftime('%d/%m/%Y'),
                         "a draft must fall back to the movement date")

        native = self._line_of(
            NativeWizard._get_ple_report_content(wizard, '1301'), move)
        self.assertEqual(native[DATE], bill.invoice_date.strftime('%d/%m/%Y'),
                         "native emits the draft's date")

    # ------------------------------------------------------------------
    # Audit -- reports, never blocks, never writes
    # ------------------------------------------------------------------
    @freeze_time('2026-01-15')
    def test_audit_flags_an_empty_existence_code(self):
        self._build_fixture()
        self.product.default_code = False

        findings = self._report()._l10n_pe_ple_audit_findings()
        self.assertIn(
            ('missing_code', self.product.id),
            {(f['kind'], f['product_id']) for f in findings})

    @freeze_time('2026-01-15')
    def test_audit_flags_a_gtin_declared_as_others(self):
        self._build_fixture()
        self.product.default_code = '7501234567890'

        findings = self._report()._l10n_pe_ple_audit_findings()
        self.assertIn(
            ('catalogue_mismatch', self.product.id),
            {(f['kind'], f['product_id']) for f in findings})

    @freeze_time('2026-01-15')
    def test_audit_flags_a_uom_without_sunat_code(self):
        self._build_fixture()
        self.product.uom_id.l10n_pe_edi_measure_unit_code = False

        findings = self._report()._l10n_pe_ple_audit_findings()
        self.assertIn('missing_uom_code', {f['kind'] for f in findings})

    @freeze_time('2026-01-15')
    def test_audit_action_lists_the_findings(self):
        self._build_fixture()
        self.product.default_code = False

        action = self._report().action_l10n_pe_ple_audit()
        self.assertEqual(action['res_model'], 'l10n_pe.stock.ple.audit.line')
        lines = self.env['l10n_pe.stock.ple.audit.line'].search(action['domain'])
        self.assertTrue(lines, "the action must list the findings")
        self.assertIn('missing_code', lines.mapped('kind'))

    def test_audit_only_covers_the_chosen_period(self):
        """The findings come from the wizard's own dates, not from everything."""
        with freeze_time('2026-01-15'):
            self._build_fixture()
            self.product.default_code = False
            january = self._report()
        self.assertTrue(january._l10n_pe_ple_audit_findings(),
                        "January carries the movements and the finding")

        february = self.env['l10n_pe.stock.ple.wizard'].create({
            'date_from': '2026-02-01',
            'date_to': '2026-02-28',
        })
        self.assertFalse(february._l10n_pe_ple_audit_findings(),
                         "February has no movements, so nothing to report")
        action = february.action_l10n_pe_ple_audit()
        self.assertEqual(action['tag'], 'display_notification',
                         "a clean period only notifies, it opens no list")

    @freeze_time('2026-01-15')
    def test_audit_returns_to_the_wizard_it_came_from(self):
        self._build_fixture()
        self.product.default_code = False
        wizard = self._report()

        action = wizard.action_l10n_pe_ple_audit()
        self.assertEqual(action['target'], 'new',
                         "the audit must stay in the dialog flow")
        self.assertEqual(action['context']['ple_wizard_id'], wizard.id)

        back = self.env['l10n_pe.stock.ple.audit.line'].with_context(
            ple_wizard_id=wizard.id).action_l10n_pe_ple_back_to_report()
        self.assertEqual(back['res_model'], 'l10n_pe.stock.ple.wizard')
        self.assertEqual(back['res_id'], wizard.id,
                         "the period the user chose must not be lost")

    @freeze_time('2026-01-15')
    def test_audit_does_not_touch_the_data(self):
        purchase, _sale = self._build_fixture()
        move = self._receipt_move(purchase)
        before = self._report()._get_ple_report_content('1301')

        self._report().action_l10n_pe_ple_audit()

        self.assertEqual(self._report()._get_ple_report_content('1301'), before,
                         "the audit must not change what the report emits")
        self.assertTrue(move.exists())
