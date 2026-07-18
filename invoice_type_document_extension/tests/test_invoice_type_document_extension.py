from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import UserError, ValidationError


@tagged('post_install', '-at_install')
class TestInvoiceTypeDocumentExtension(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref('sales_team.group_sale_salesman')
        cls.env.user.group_ids += cls.env.ref('purchase.group_purchase_user')

        cls.pe_country = cls.env.ref('base.pe')
        cls.env.company.write({'country_id': cls.pe_country.id})

        # Sale/purchase journals use documents (matches the PE scenario).
        cls.env['account.journal'].search([
            ('type', 'in', ('sale', 'purchase')),
            ('company_id', '=', cls.env.company.id),
        ]).write({'l10n_latam_use_documents': True})

        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'is_storable': True,
        })
        # Factura (01) with a document code prefix -> a manual document number
        # survives posting cleanly ('F001-1001').
        cls.doc_type = cls.env['l10n_latam.document.type'].create({
            'name': 'Factura',
            'code': '01',
            'doc_code_prefix': 'F',
            'country_id': cls.pe_country.id,
        })
        # Same type WITHOUT a prefix -> posting yields the 'False <num>'
        # placeholder used to exercise the "'False '" discard rule.
        cls.doc_type_noprefix = cls.env['l10n_latam.document.type'].create({
            'name': 'Factura sin prefijo',
            'code': '01',
            'country_id': cls.pe_country.id,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_purchase(self, qty=10.0):
        po = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': qty,
                'price_unit': 100.0,
            })],
        })
        po.button_confirm()
        return po

    def _make_bill(self, po, doc_number='F001-1001', doc_type=None, post=True):
        doc_type = doc_type if doc_type is not None else self.doc_type
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'invoice_date': '2024-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': po.order_line[0].product_qty,
                'price_unit': 100.0,
                'purchase_line_id': po.order_line[0].id,
            })],
        })
        vals = {}
        if doc_type:
            vals['l10n_latam_document_type_id'] = doc_type.id
        if doc_number is not None:
            vals['l10n_latam_manual_document_number'] = True
            vals['l10n_latam_document_number'] = doc_number
        bill.write(vals)
        if post:
            bill.action_post()
        return bill

    def _receipt_move(self, po):
        return po.picking_ids.move_ids[:1]

    def _validate_receipt(self, po):
        picking = po.picking_ids
        picking.move_line_ids.write({'picked': True})
        for ml in picking.move_line_ids:
            ml.quantity = ml.move_id.product_qty
        picking.button_validate()

    def _expected(self, invoice):
        """Serie/folio the capture should derive from the invoice's real,
        post-formatting document number (l10n_pe zero-pads the folio, so the
        exact digits depend on whether the localization is installed)."""
        return self.env['stock.move']._itde_get_serie_folio(
            invoice.l10n_latam_document_number)

    # ------------------------------------------------------------------
    # _get_serie_folio parity with the native wizard (decision A1)
    # ------------------------------------------------------------------
    def test_serie_folio_parity(self):
        Move = self.env['stock.move']
        cases = {
            'F001-00001001': ('F001', '00001001'),
            'REF-2002': ('REF', '2002'),
            'F0015005': ('F', '0015005'),        # only the trailing digit run
            'F001-01-0009': ('F00101', '0009'),  # multi-hyphen: serie strips '-'
        }
        for number, (serie, folio) in cases.items():
            parsed = Move._itde_get_serie_folio(number)
            self.assertEqual(parsed['folio'], folio, "folio for %s" % number)
            self.assertEqual(parsed['serie'], serie, "serie for %s" % number)

    # ------------------------------------------------------------------
    # Priority: l10n_latam_document_number (canonical) is captured per move.
    # ------------------------------------------------------------------
    def test_priority_document_number(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        bill = self._make_bill(po, doc_number='F001-1001')
        move._itde_populate_documents()
        expected = self._expected(bill)
        self.assertEqual(move.transfer_document_type_id, self.doc_type)
        self.assertEqual(move.serie_transfer_document, 'F001')
        self.assertEqual(move.number_transfer_document, expected['folio'])

    # ------------------------------------------------------------------
    # "'False '" rule: a document with no prefix posts as 'False <num>' ->
    # discard (leave empty -> native fallback), never emit a 'False' serie.
    # ------------------------------------------------------------------
    def test_false_prefix_discarded(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        bill = self._make_bill(po, doc_number='F001-1001',
                               doc_type=self.doc_type_noprefix)
        self.assertTrue(bill.l10n_latam_document_number.startswith('False'),
                        "precondition: no-prefix type yields the 'False ' placeholder")
        move._itde_populate_documents()
        self.assertFalse(move.transfer_document_type_id,
                         "'False ' number must leave the fields empty")

    # ------------------------------------------------------------------
    # No backing invoice (internal transfer / traslado) -> stays empty ->
    # the bridge inherits the native guide (09).
    # ------------------------------------------------------------------
    def test_internal_transfer_stays_empty(self):
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1)
        picking = self.env['stock.picking'].create({
            'picking_type_id': warehouse.int_type_id.id,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': warehouse.lot_stock_id.id,
            'move_ids': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 3.0,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': warehouse.lot_stock_id.id,
            })],
        })
        move = picking.move_ids
        move._itde_populate_documents()
        self.assertFalse(move.transfer_document_type_id)

    # ------------------------------------------------------------------
    # Event: posting the bill fills the receipt move (super-first _post).
    # ------------------------------------------------------------------
    def test_event_post_fills_move(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        self.assertFalse(move.transfer_document_type_id)
        bill = self._make_bill(po, doc_number='F001-1001')
        self.assertEqual(move.transfer_document_type_id, self.doc_type)
        self.assertEqual(move.serie_transfer_document, 'F001')
        self.assertEqual(move.number_transfer_document, self._expected(bill)['folio'])

    # ------------------------------------------------------------------
    # Sale flow: exercises the sale_line_ids (plural) propagation path.
    # ------------------------------------------------------------------
    def test_sale_flow_fills_move(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'price_unit': 100.0,
            })],
        })
        so.action_confirm()
        move = so.picking_ids.move_ids[:1]
        invoice = so._create_invoices()
        invoice.write({
            'invoice_date': '2024-01-01',
            'l10n_latam_document_type_id': self.doc_type.id,
            'l10n_latam_manual_document_number': True,
            'l10n_latam_document_number': 'F002-5005',
        })
        invoice.action_post()
        move._itde_populate_documents()
        self.assertEqual(move.transfer_document_type_id, self.doc_type)
        self.assertEqual(move.serie_transfer_document, 'F002')
        self.assertEqual(move.number_transfer_document, self._expected(invoice)['folio'])

    # ------------------------------------------------------------------
    # manual_override: a manual edit is never clobbered by events/force.
    # ------------------------------------------------------------------
    def test_manual_override_persists(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        move.write({
            'serie_transfer_document': 'MAN',
            'number_transfer_document': '9999',
            'transfer_document_type_id': self.doc_type.id,
        })
        self.assertTrue(move.manual_override, "manual write must set the flag")
        self._make_bill(po, doc_number='F001-1001')  # posting must not overwrite
        self.assertEqual(move.serie_transfer_document, 'MAN')
        self.assertEqual(move.number_transfer_document, '9999')
        move.action_itde_force()  # force (non-manual) must also skip it
        self.assertEqual(move.serie_transfer_document, 'MAN')

    def test_auto_populate_does_not_set_flag(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        self._make_bill(po, doc_number='F001-1001')
        move._itde_populate_documents()
        self.assertFalse(move.manual_override,
                         "programmatic population must never set manual_override")

    # ------------------------------------------------------------------
    # Constraint (SUNAT: <=20 chars, positive)
    # ------------------------------------------------------------------
    def test_constraint_length(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        with self.assertRaises(ValidationError):
            move.write({'serie_transfer_document': 'X' * 21})

    def test_constraint_negative_number(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        with self.assertRaises(ValidationError):
            move.write({'number_transfer_document': '-5'})

    # ------------------------------------------------------------------
    # Mass action: fill-empty skips a not-yet-posted invoice; force re-derives.
    # ------------------------------------------------------------------
    def test_mass_fill_empty_skips_unposted(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        self._make_bill(po, doc_number='F001-1001', post=False)
        move.action_itde_fill_empty()
        self.assertFalse(move.transfer_document_type_id)

    def test_force_rederives_non_manual(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        bill = self._make_bill(po, doc_number='F001-1001')
        expected_folio = self._expected(bill)['folio']
        self.assertEqual(move.number_transfer_document, expected_folio)
        # Corrupt a NON-manual value (auto context -> flag stays False).
        move.with_context(auto_populate=True).write(
            {'number_transfer_document': 'BAD'})
        self.assertFalse(move.manual_override)
        move.action_itde_force()
        self.assertEqual(move.number_transfer_document, expected_folio)

    # ------------------------------------------------------------------
    # LATAM scope gate: a non-LATAM company leaves the fields empty.
    # ------------------------------------------------------------------
    def test_non_latam_company_empty(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        self._make_bill(po, doc_number='F001-1001')
        move.action_itde_force()
        self.assertEqual(move.transfer_document_type_id, self.doc_type)
        move._itde_clear_auto()
        narnia = self.env['res.country'].create({'name': 'Narnia', 'code': 'NN'})
        self.env.company.country_id = narnia
        move.action_itde_force()
        self.assertFalse(move.transfer_document_type_id,
                         "non-LATAM company must leave the fields empty")

    # ------------------------------------------------------------------
    # Draft/cancel of the invoice clears the NON-manual value it populated.
    # ------------------------------------------------------------------
    def test_draft_clears_non_manual(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        bill = self._make_bill(po, doc_number='F001-1001')
        self.assertEqual(move.number_transfer_document, self._expected(bill)['folio'])
        bill.button_draft()
        self.assertFalse(move.transfer_document_type_id,
                         "resetting the invoice to draft clears the auto value")

    # ------------------------------------------------------------------
    # The mass action never wipes a MANUAL value, even when the re-derivation
    # would come out empty (the user's manual entry is preserved).
    # ------------------------------------------------------------------
    def test_mass_force_preserves_manual(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        move.write({
            'serie_transfer_document': 'MAN',
            'number_transfer_document': '7',
            'transfer_document_type_id': self.doc_type.id,
        })
        self.assertTrue(move.manual_override)
        # No posted invoice -> re-derivation is empty; manual must survive.
        move.action_itde_force()
        self.assertEqual(move.serie_transfer_document, 'MAN')
        self.assertEqual(move.number_transfer_document, '7')

    # ------------------------------------------------------------------
    # Anti-empty guard: an empty re-derivation never wipes an existing value,
    # even a non-manual one.
    # ------------------------------------------------------------------
    def test_force_empty_result_does_not_wipe(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        move.with_context(auto_populate=True).write({
            'serie_transfer_document': 'AUTO',
            'number_transfer_document': '5',
            'transfer_document_type_id': self.doc_type.id,
        })
        self.assertFalse(move.manual_override)
        move.action_itde_force()  # no invoice, no guide -> empty -> keep value
        self.assertEqual(move.serie_transfer_document, 'AUTO')
        self.assertEqual(move.number_transfer_document, '5')

    # ------------------------------------------------------------------
    # Re-runnable range wizard: re-derive from invoices over a date range.
    # ------------------------------------------------------------------
    def test_range_wizard_rederive(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        self._validate_receipt(po)  # move must be done to enter the PLE range
        bill = self._make_bill(po, doc_number='F001-1001')
        move._itde_clear_auto()  # start empty to prove the wizard fills it
        self.assertFalse(move.transfer_document_type_id)
        self.env['stock.transfer.document.range.populate'].create({
            'date_from': '2020-01-01',
            'date_to': '2035-12-31',
            'mode': 'rederive',
        }).action_run()
        self.assertEqual(move.transfer_document_type_id, self.doc_type)
        self.assertEqual(move.number_transfer_document, self._expected(bill)['folio'])

    # ------------------------------------------------------------------
    # Re-runnable range wizard: copy legacy picking values over a date range.
    # ------------------------------------------------------------------
    def test_range_wizard_copy_legacy(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        move.picking_id.write({
            'serie_transfer_document': 'LEG',
            'number_transfer_document': '77',
        })
        self.env['stock.transfer.document.range.populate'].create({
            'date_from': '2020-01-01',
            'date_to': '2035-12-31',
            'mode': 'copy_legacy',
        }).action_run()
        move.invalidate_recordset()
        self.assertEqual(move.serie_transfer_document, 'LEG')
        self.assertEqual(move.number_transfer_document, '77')
        self.assertTrue(move.manual_override)

    # ------------------------------------------------------------------
    # "Recover Serie & Correlativo" action: copy the legacy picking value onto
    # the selected moves (same as the migration, on demand).
    # ------------------------------------------------------------------
    def test_recover_legacy_action(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        move.picking_id.write({
            'transfer_document_type_id': self.doc_type.id,
            'serie_transfer_document': 'REC',
            'number_transfer_document': '55',
        })
        move.action_itde_recover_legacy()
        move.invalidate_recordset()
        self.assertEqual(move.transfer_document_type_id, self.doc_type)
        self.assertEqual(move.serie_transfer_document, 'REC')
        self.assertEqual(move.number_transfer_document, '55')
        self.assertTrue(move.manual_override)

    # ==================================================================
    # Consolidated wizard: stock.transfer.document.manage
    # ==================================================================
    def _wizard(self, moves, **vals):
        """Open the manage wizard on ``moves`` as the list Action menu would
        (active_ids in context -> default_get seeds move_ids)."""
        return self.env['stock.transfer.document.manage'].with_context(
            active_model='stock.move', active_ids=moves.ids,
        ).create(vals)

    def _auto_fill(self, move, serie, number):
        """Stamp a NON-manual (automatic) value onto a move."""
        move.with_context(auto_populate=True).write({
            'transfer_document_type_id': self.doc_type.id,
            'serie_transfer_document': serie,
            'number_transfer_document': number,
        })

    def _manual_fill(self, move, serie, number):
        move.write({
            'transfer_document_type_id': self.doc_type.id,
            'serie_transfer_document': serie,
            'number_transfer_document': number,
        })

    # ------------------------------------------------------------------
    # default_get seeds the selection; empty selection is refused on apply.
    # ------------------------------------------------------------------
    def test_wizard_default_get_seeds_moves(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        wiz = self._wizard(move, strategy='fill_empty')
        self.assertEqual(wiz.move_ids, move)
        self.assertEqual(wiz.count_selected, 1)

    def test_wizard_empty_selection_raises(self):
        wiz = self.env['stock.transfer.document.manage'].create(
            {'strategy': 'fill_empty'})
        self.assertFalse(wiz.move_ids)
        with self.assertRaises(UserError):
            wiz.action_apply()

    # ------------------------------------------------------------------
    # Live counts + banner colour react to the selection and the strategy.
    # ------------------------------------------------------------------
    def test_wizard_counts_and_banner(self):
        po1 = self._make_purchase()
        m_empty = self._receipt_move(po1)
        po2 = self._make_purchase()
        m_auto = self._receipt_move(po2)
        self._auto_fill(m_auto, 'AUTO', '1')
        self.assertFalse(m_auto.manual_override)
        po3 = self._make_purchase()
        m_manual = self._receipt_move(po3)
        self._manual_fill(m_manual, 'MAN', '2')
        self.assertTrue(m_manual.manual_override)

        moves = m_empty | m_auto | m_manual
        wiz = self._wizard(moves, strategy='fill_empty')
        self.assertEqual(wiz.count_selected, 3)
        self.assertEqual(wiz.count_empty, 1)
        self.assertEqual(wiz.count_auto, 1)
        self.assertEqual(wiz.count_manual, 1)
        self.assertIn('alert-success', wiz.banner)  # fill_empty = safe
        # Banner defines each category and flags the "some empties can't fill" gap.
        self.assertIn('no document yet', wiz.banner)
        self.assertIn('stay empty', wiz.banner)

        wiz.strategy = 'rederive'
        self.assertIn('alert-warning', wiz.banner)  # re-derive = caution
        self.assertIn('never wipes an existing value', wiz.banner)  # anti-empty note
        wiz.include_manual = True
        self.assertIn('alert-danger', wiz.banner)   # overwrites manuals = danger

    # ------------------------------------------------------------------
    # Parity: each strategy leaves the same state as the button it replaces.
    # ------------------------------------------------------------------
    def test_wizard_fill_empty_fills_only_empty(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        bill = self._make_bill(po, doc_number='F001-1001')  # event auto-fills
        move._itde_clear_auto()  # back to empty to prove the wizard fills it
        self.assertFalse(move.transfer_document_type_id)
        self._wizard(move, strategy='fill_empty').action_apply()
        self.assertEqual(move.transfer_document_type_id, self.doc_type)
        self.assertEqual(move.number_transfer_document, self._expected(bill)['folio'])

    def test_wizard_rederive_overwrites_auto_keeps_manual(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        bill = self._make_bill(po, doc_number='F001-1001')
        expected = self._expected(bill)['folio']
        # Corrupt a NON-manual value; a manual move stays untouched.
        move.with_context(auto_populate=True).write(
            {'number_transfer_document': 'BAD'})
        self.assertFalse(move.manual_override)
        po2 = self._make_purchase()
        manual = self._receipt_move(po2)
        self._manual_fill(manual, 'MAN', '9999')
        self._wizard(move | manual, strategy='rederive').action_apply()
        self.assertEqual(move.number_transfer_document, expected)
        self.assertEqual(manual.number_transfer_document, '9999')  # protected

    def test_wizard_rederive_include_manual_overwrites_manual(self):
        """The formerly unreachable force-including-manual path, via the UI."""
        po = self._make_purchase()
        move = self._receipt_move(po)
        self._manual_fill(move, 'MAN', '9999')
        self.assertTrue(move.manual_override)
        bill = self._make_bill(po, doc_number='F001-1001')  # won't touch manual
        self.assertEqual(move.number_transfer_document, '9999')
        self._wizard(move, strategy='rederive', include_manual=True).action_apply()
        self.assertEqual(move.number_transfer_document, self._expected(bill)['folio'])

    def test_wizard_recover_legacy(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        move.picking_id.write({
            'transfer_document_type_id': self.doc_type.id,
            'serie_transfer_document': 'REC',
            'number_transfer_document': '55',
        })
        wiz = self._wizard(move, strategy='recover_legacy')
        self.assertTrue(wiz.legacy_available)
        wiz.action_apply()
        move.invalidate_recordset()
        self.assertEqual(move.serie_transfer_document, 'REC')
        self.assertEqual(move.number_transfer_document, '55')
        self.assertTrue(move.manual_override)

    # ------------------------------------------------------------------
    # recover_legacy honours the same include_manual axis as re-derive:
    # by DEFAULT a hand-edited move is protected; only include_manual clobbers it.
    # ------------------------------------------------------------------
    def _picking_legacy(self, move, serie, number):
        move.picking_id.write({
            'transfer_document_type_id': self.doc_type.id,
            'serie_transfer_document': serie,
            'number_transfer_document': number,
        })

    def test_wizard_recover_legacy_protects_manual_by_default(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        self._manual_fill(move, 'MAN', '9999')
        self.assertTrue(move.manual_override)
        self._picking_legacy(move, 'REC', '55')
        wiz = self._wizard(move, strategy='recover_legacy')
        self.assertFalse(wiz.include_manual)  # default: protect manuals
        self.assertIn('alert-warning', wiz.banner)
        self.assertIn('Up to', wiz.banner)  # explains why the count is a ceiling
        self.assertEqual(wiz.count_will_change, 0)  # the only move is manual
        wiz.action_apply()
        move.invalidate_recordset()
        self.assertEqual(move.serie_transfer_document, 'MAN')  # untouched
        self.assertEqual(move.number_transfer_document, '9999')

    def test_wizard_recover_legacy_include_manual_overwrites(self):
        po = self._make_purchase()
        move = self._receipt_move(po)
        self._manual_fill(move, 'MAN', '9999')
        self._picking_legacy(move, 'REC', '55')
        wiz = self._wizard(move, strategy='recover_legacy', include_manual=True)
        self.assertIn('alert-danger', wiz.banner)  # danger: overwrites manuals
        wiz.action_apply()
        move.invalidate_recordset()
        self.assertEqual(move.serie_transfer_document, 'REC')  # overwritten
        self.assertEqual(move.number_transfer_document, '55')
        self.assertTrue(move.manual_override)

    # ------------------------------------------------------------------
    # Honesty: count_will_change counts ONLY movements that really change.
    # ------------------------------------------------------------------
    def test_wizard_will_change_counts_only_real_changes(self):
        po_a = self._make_purchase()
        m_a = self._receipt_move(po_a)
        self._make_bill(po_a, doc_number='F001-1001')
        m_a.with_context(auto_populate=True).write(
            {'number_transfer_document': 'BAD'})  # would change
        po_b = self._make_purchase()
        m_b = self._receipt_move(po_b)
        bill_b = self._make_bill(po_b, doc_number='F001-2002')
        self.assertEqual(m_b.number_transfer_document,
                         self._expected(bill_b)['folio'])  # already correct
        wiz = self._wizard(m_a | m_b, strategy='rederive')
        self.assertEqual(wiz.count_will_change, 1)
        affected = wiz.action_view_affected()
        self.assertEqual(affected['domain'], [('id', 'in', m_a.ids)])
