# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestReportRendering(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Picking = cls.env['stock.picking']
        cls.Move = cls.env['stock.move']
        cls.Partner = cls.env['res.partner']
        cls.Product = cls.env['product.product']
        cls.PickingType = cls.env['stock.picking.type']
        
        # Create common data
        cls.partner = cls.Partner.create({'name': 'Test Partner'})
        cls.product = cls.Product.create({
            'name': 'Test Product',
            'type': 'consu',
        })
        cls.picking_type = cls.PickingType.search([], limit=1)
        if not cls.picking_type:
            cls.picking_type = cls.env['stock.picking.type'].create({
                'name': 'Test Type',
                'code': 'outgoing',
                'sequence_code': 'TEST',
            })
        cls.location_src = cls.picking_type.default_location_src_id or cls.env.ref('stock.stock_location_stock')
        cls.location_dest = cls.picking_type.default_location_dest_id or cls.env.ref('stock.stock_location_customers')

    def test_rendering_draft_state(self):
        """ Test rendering report in 'draft' state to verify 'move_ids' usage """
        picking = self.Picking.create({
            'partner_id': self.partner.id,
            'picking_type_id': self.picking_type.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
            'state': 'draft',
        })
        
        move = self.Move.create({

            'product_id': self.product.id,
            'product_uom_qty': 10,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })

        # Get Report Action
        report = self.env.ref('l10n_pe_classic_format_picking.stock_picking_classic')
        
        # Render - no try/except so the FULL traceback is visible in the test runner
        report._render_qweb_html(report.id, picking.ids)

    def test_rendering_done_state_with_packages(self):
        """ Test rendering report in 'done' state with packages to verify 'package_history_ids' usage """
        picking = self.Picking.create({
            'partner_id': self.partner.id,
            'picking_type_id': self.picking_type.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })
        
        move = self.Move.create({

            'product_id': self.product.id,
            'product_uom_qty': 5,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location_src.id,
            'location_dest_id': self.location_dest.id,
        })
        
        picking.action_confirm()
        picking.action_assign()
        
        # Set quantity and package
        move.move_line_ids.quantity = 5
        package = self.env['stock.package'].create({'name': 'Test Pack 1'})
        move.move_line_ids.result_package_id = package
        
        picking.button_validate()
        
        self.assertEqual(picking.state, 'done', "Picking should be in 'done' state")
        
        # Get Report Action
        report = self.env.ref('l10n_pe_classic_format_picking.stock_picking_classic')
        
        # Try rendering
        try:
            report._render_qweb_html(report.id, picking.ids)
        except Exception as e:
            self.fail(f"Report rendering failed in 'done' state with packages: {e}")
