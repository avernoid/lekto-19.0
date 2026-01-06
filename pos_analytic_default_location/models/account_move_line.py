from odoo import models

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_analytic_distribution_arguments(self, root_plans):
        """ Override to add pos_config_id to the arguments if available. """
        args = super()._get_analytic_distribution_arguments(root_plans)
        
        pos_config_id = self.env.context.get('pos_config_id')
        
        # If not in context, try to find it via links
        if not pos_config_id:
            # Case 1: Invoiced POS Order
            if self.move_id.pos_order_ids:
                pos_config_id = self.move_id.pos_order_ids[0].config_id.id
                
            # Case 2: POS Session Closing Move
            elif hasattr(self.move_id, 'pos_session_id') and self.move_id.pos_session_id:
                pos_config_id = self.move_id.pos_session_id.config_id.id
            
            # Case 3: Stock Move related (Delivery/Receipt)
            elif self.move_id.stock_move_ids:
                stock_move = self.move_id.stock_move_ids[0]
                picking = stock_move.picking_id
                if picking and hasattr(picking, 'pos_order_id') and picking.pos_order_id:
                    pos_config_id = picking.pos_order_id.config_id.id
        
        if pos_config_id:
            args['pos_config_id'] = pos_config_id
            
        return args

