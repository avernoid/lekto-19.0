import hashlib
import inspect

from freezegun import freeze_time

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged

from odoo.addons.l10n_pe_reports_stock.wizard.stock_move_ple_report import (
    L10n_PeStockPleWizard as NativeWizard,
)

# sha256 of inspect.getsource(NativeWizard._get_ple_report_content).  If Odoo
# updates the native method, this fingerprint changes and the test fails HARD:
# the bridge copies that method verbatim and MUST be re-synced before deploy or
# the PLE TXT can silently diverge from what SUNAT expects.
NATIVE_FINGERPRINT = '8184a8e1177e1cc3102f1826900368481882070d1d69cdcc387cdda2b40b21f7'

DRIFT_MESSAGE = (
    "PLE bridge diverges from native: Odoo updated "
    "l10n_pe_reports_stock._get_ple_report_content; the TXT may be wrong for "
    "SUNAT. Re-sync the copied method in "
    "l10n_pe_reports_stock_transfer_document before deploying."
)


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPleBridgeRegression(TestSaleCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.country_id = cls.env.ref("base.pe")
        cls.company.vat = "20512528458"
        cls.partner_a.write({
            "country_id": cls.env.ref("base.pe").id,
            "vat": "20557912879",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_RUC").id,
        })
        cls.doc_type_01 = cls.env.ref("l10n_pe.document_type01")

        cls.product = cls.company_data['product_order_no']
        cls.product.categ_id.property_cost_method = "average"
        cls.product.is_storable = True

        cls.product2 = cls.env['product.product'].create({
            'name': 'Second Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.product.categ_id.id,
        })

    # ------------------------------------------------------------------
    # Fixture: a report period exercising several native branches at once.
    # ------------------------------------------------------------------
    def _build_fixture(self):
        # Purchase receipt + posted bill (invoice document line).
        purchase = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_qty': 5.0,
                    'product_uom_id': self.product.uom_id.id,
                    'price_unit': 500.0,
                }),
                Command.create({
                    'name': self.product2.name,
                    'product_id': self.product2.id,
                    'product_qty': 4.0,
                    'product_uom_id': self.product2.uom_id.id,
                    'price_unit': 100.0,
                }),
            ],
        })
        purchase.button_confirm()
        picking = purchase.picking_ids
        picking.move_line_ids.write({'picked': True})
        for ml in picking.move_line_ids:
            ml.quantity = ml.move_id.product_qty
        picking.button_validate()

        purchase.action_create_invoice()
        bill = purchase.invoice_ids
        bill.write({
            'invoice_date': self.report_date,
            'l10n_latam_document_type_id': self.doc_type_01.id,
            'l10n_latam_document_number': "BILL/2026/01/0001",
        })
        bill.action_post()

        # Sale delivery (customer, 'out' move -> exercises the sale/guide
        # branch).  The customer invoice is intentionally NOT posted: PE
        # e-invoicing (l10n_pe_edi) would require full EDI configuration, and
        # the report only needs the done move.
        sale = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 2.0,
                'price_unit': 800.0,
            })],
        })
        sale.action_confirm()
        out_picking = sale.picking_ids
        out_picking.move_line_ids.write({'picked': True})
        for ml in out_picking.move_line_ids:
            ml.quantity = ml.move_id.product_uom_qty
        out_picking.button_validate()
        return purchase, sale

    def _report(self):
        return self.env['l10n_pe.stock.ple.wizard'].create({
            'date_from': '2026-01-01',
            'date_to': '2026-01-31',
        })

    def _clear_transfer_fields(self):
        """Reset the capture -- the companion module auto-fills receipt moves on
        bill posting; the bridge regression must start from a clean slate."""
        moves = self.env['stock.move'].search(
            [('company_id', '=', self.company.id)])
        moves.with_context(auto_populate=True).write({
            'transfer_document_type_id': False,
            'serie_transfer_document': False,
            'number_transfer_document': False,
            'manual_override': False,
        })
        # The move-level SUNAT operation type (l10n_pe_stock_operation_type)
        # auto-populates on validation too; clear it so the no-op comparison
        # starts from a genuinely empty capture.  Guarded: inert when that
        # module is not installed.  The manual flag is set in the same write so
        # the provenance gate is bypassed (no context needed).
        if 'l10n_pe_operation_type' in moves._fields:
            moves.write({
                'l10n_pe_operation_type': False,
                'l10n_pe_operation_type_manual': False,
            })

    report_date = '2026-01-15'

    # ------------------------------------------------------------------
    # 1) FINGERPRINT - hard fail if the native method drifts (MANDATORY).
    # ------------------------------------------------------------------
    def test_native_source_fingerprint(self):
        actual = hashlib.sha256(
            inspect.getsource(NativeWizard._get_ple_report_content).encode()
        ).hexdigest()
        if NATIVE_FINGERPRINT == 'BOOTSTRAP':
            self.fail("ITDE-FINGERPRINT actual=%s" % actual)
        self.assertEqual(actual, NATIVE_FINGERPRINT, DRIFT_MESSAGE)

    # ------------------------------------------------------------------
    # 2) NO-OP: with every transfer_* field empty, the bridge output must be
    #    byte-identical to the native output (native-vs-bridge comparison).
    # ------------------------------------------------------------------
    @freeze_time('2026-01-15')
    def test_bridge_is_noop_when_unpopulated(self):
        self._build_fixture()
        self._clear_transfer_fields()
        wizard = self._report()

        moves = wizard._get_ple_reports_data()
        self.assertTrue(moves, "fixture must yield moves in the period")
        # False-positive guard: assert the injection is genuinely inert.
        for move in moves:
            self.assertFalse(move.transfer_document_type_id)
            self.assertFalse(move.serie_transfer_document)
            self.assertFalse(move.number_transfer_document)

        for report_number in ('1301', '1201'):
            ours = wizard._get_ple_report_content(report_number)
            native = NativeWizard._get_ple_report_content(wizard, report_number)
            self.assertEqual(ours, native,
                             "bridge must be a no-op for report %s when the "
                             "transfer fields are empty" % report_number)

    # ------------------------------------------------------------------
    # 3) INJECTION: a populated move overrides type + serie + folio atomically.
    # ------------------------------------------------------------------
    @freeze_time('2026-01-15')
    def test_injection_overrides_document(self):
        purchase, _sale = self._build_fixture()
        self._clear_transfer_fields()
        receipt_move = purchase.picking_ids.move_ids.filtered(
            lambda m: m.product_id == self.product)[:1]
        receipt_move.with_context(auto_populate=True).write({
            'transfer_document_type_id': self.doc_type_01.id,
            'serie_transfer_document': 'F001',
            'number_transfer_document': '00099',
        })
        wizard = self._report()
        content = wizard._get_ple_report_content('1301')
        line = [
            ln for ln in content.split('\n')
            if ln and ln.split('|')[1] == str(receipt_move.id).zfill(6)
        ]
        self.assertTrue(line, "the populated move must have a line")
        fields = line[0].split('|')
        # Layout: period(0) cuo(1) number(2) establishment(3) catalogue(4)
        # type_of_existence(5) default_code(6) catalogue_used(7) unspsc(8)
        # date(9) document_type(10) serie(11) folio(12) ...
        self.assertEqual(fields[10], self.doc_type_01.code,
                         "captured document type must reach the line")
        self.assertEqual(fields[11], 'F001', "captured serie must reach the line")
        self.assertEqual(fields[12], '00099', "captured folio must reach the line")

    # ------------------------------------------------------------------
    # 4) GATE: serie/folio present but NO type -> no injection (never '00'
    #    post-forcing).  Output identical to native for that move.
    # ------------------------------------------------------------------
    @freeze_time('2026-01-15')
    def test_gate_requires_type(self):
        purchase, _sale = self._build_fixture()
        self._clear_transfer_fields()
        receipt_move = purchase.picking_ids.move_ids.filtered(
            lambda m: m.product_id == self.product)[:1]
        # Serie/folio set but type empty -> gate closed -> native stands.
        receipt_move.with_context(auto_populate=True).write({
            'serie_transfer_document': 'X999',
            'number_transfer_document': '12345',
        })
        wizard = self._report()
        ours = wizard._get_ple_report_content('1301')
        native = NativeWizard._get_ple_report_content(wizard, '1301')
        self.assertEqual(ours, native,
                         "no captured type -> the bridge must not inject")

    # ------------------------------------------------------------------
    # 5) GUIDE FALLBACK: a move with NO invoice but a remission guide gets
    #    populated with type '09' + the guide serie/folio, and the bridge line
    #    still matches native (guide = native's own '09' handling).
    #    Requires l10n_pe_edi_stock (the remission-guide field on the picking).
    # ------------------------------------------------------------------
    def test_guide_document_type_resolves_09(self):
        """The guide document type is resolved by SUNAT code '09' (not from the
        picking's reason-for-transfer).  Runs without l10n_pe_edi_stock."""
        guide_type = self.env['l10n_latam.document.type'].search(
            [('code', '=', '09'), ('country_id.code', '=', 'PE')], limit=1)
        if not guide_type:
            self.skipTest("no PE document type with code 09")
        move = self.env['stock.move'].new({'company_id': self.company.id})
        self.assertEqual(move._itde_guide_document_type(), guide_type)

    @freeze_time('2026-01-15')
    def test_guide_fallback_populates_09(self):
        if 'l10n_latam_document_number' not in self.env['stock.picking']._fields:
            self.skipTest("l10n_pe_edi_stock not installed (no remission guide field)")
        guide_type = self.env['l10n_latam.document.type'].search(
            [('code', '=', '09'), ('country_id.code', '=', 'PE')], limit=1)
        if not guide_type:
            self.skipTest("no PE document type with code 09")

        _purchase, sale = self._build_fixture()
        self._clear_transfer_fields()
        picking = sale.picking_ids
        picking.l10n_latam_document_number = 'T001-00000123'  # remission guide
        move = picking.move_ids[:1]

        move._itde_populate_documents(force=True)
        self.assertEqual(move.transfer_document_type_id, guide_type,
                         "a guide-only move must get document type 09")
        self.assertEqual(move.serie_transfer_document, 'T001')
        self.assertEqual(move.number_transfer_document, '00000123')

        # The injected guide reproduces what native already emits for the guide.
        wizard = self._report()
        ours = wizard._get_ple_report_content('1301')
        native = NativeWizard._get_ple_report_content(wizard, '1301')
        self.assertEqual(ours, native,
                         "guide injection must match the native '09' handling")

    # ------------------------------------------------------------------
    # 6) OPERATION-TYPE INJECTION: a move carrying a per-move SUNAT operation
    #    type (from l10n_pe_stock_operation_type) overrides the picking-derived
    #    value in the PLE.  Skipped when that capture module is not installed.
    # ------------------------------------------------------------------
    @freeze_time('2026-01-15')
    def test_operation_type_injection_overrides_picking(self):
        if 'l10n_pe_operation_type' not in self.env['stock.move']._fields:
            self.skipTest("l10n_pe_stock_operation_type not installed")
        purchase, _sale = self._build_fixture()
        self._clear_transfer_fields()
        receipt_move = purchase.picking_ids.move_ids.filtered(
            lambda m: m.product_id == self.product)[:1]
        receipt_move.with_context(l10n_pe_op_auto=True).write({
            'l10n_pe_operation_type': '18',  # Import -> not 2 (native incoming)
        })
        wizard = self._report()
        content = wizard._get_ple_report_content('1301')
        line = [
            ln for ln in content.split('\n')
            if ln and ln.split('|')[1] == str(receipt_move.id).zfill(6)
        ]
        self.assertTrue(line, "the move must have a line")
        # Layout ... document_type(10) serie(11) folio(12) operation_type(13)
        self.assertEqual(line[0].split('|')[13], '18',
                         "captured operation type must override the picking value")
