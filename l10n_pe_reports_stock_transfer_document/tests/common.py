"""Shared fixture for the PLE bridge tests.

Kept out of the test classes so the normative-field tests can build the same
period without re-running the regression suite.
"""

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.sale.tests.common import TestSaleCommon


class PleBridgeCommon(TestSaleCommon):

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
        # Credit note: the return branch of field 10 needs a document
        # type whose code is 07, to assert the row is dated by the
        # document it actually reports.
        cls.doc_type_07 = cls.env.ref("l10n_pe.document_type07")

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

    # Columns the bridge deliberately emits differently from native: field 5
    # (catalogue of the existence code, native hardcodes '1') and field 8
    # (catalogue of field 9, native hardcodes '1' even with field 9 empty).
    # Blanked on BOTH sides so the no-op guarantee still covers every other
    # column; what they must contain is asserted in test_normative_fields.
    NORMATIVE_COLUMNS = (4, 7)

    def _blank_normative_columns(self, content):
        lines = []
        for line in content.split('\n'):
            if not line:
                lines.append(line)
                continue
            columns = line.split('|')
            for index in self.NORMATIVE_COLUMNS:
                if index < len(columns):
                    columns[index] = ''
            lines.append('|'.join(columns))
        return '\n'.join(lines)
