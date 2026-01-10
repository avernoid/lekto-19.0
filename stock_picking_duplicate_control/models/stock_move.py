from odoo import api, models, _

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.onchange('product_id', 'description_picking')
    def _onchange_product_id_check_duplicates(self):
        if not self.product_id or not self.picking_id:
            return

        policy = self.picking_id.picking_type_id.duplicate_product_policy
        if policy == 'allow':
            return

        # Prepare current line comparison key
        current_desc = self.description_picking or ''
        # We need to check against existing moves in the picking
        # Note: self.id might be a NewId, preventing simple ID exclusion.
        # We iterate over other moves in the picking.
        
        # Accessing the parent picking's moves (lines)
        # In NewId context, picking_id.move_ids_without_package might contain the current record itself if it's already linked?
        # Usually in onchange, we check against the lines currently in the parent view.
        
        is_duplicate = False
        # Merge moves from both relations to handle NewId context where one might be empty but the other populated by the view
        existing_moves = self.picking_id.move_ids | self.picking_id.move_ids_without_package
        
        matches = [
            m for m in existing_moves 
            if m.product_id == self.product_id 
            and (m.description_picking or '') == current_desc
            and m.state not in ('cancel', 'done')
            # Important: Filter out 'self' from the check if possible to see if there is *another* one.
            # But self might be a NewId and m might be a NewId.
            # Comparison of NewIds: NewId(origin=1) == NewId(origin=1).
            and m != self
        ]

        if matches:

            msg = _("The product '%(name)s' already exists with the description '%(desc)s'.") % {
                'name': self.product_id.display_name,
                'desc': current_desc,
            }
            
            if policy == 'block':
                msg += " " + _("Modify the description if you wish to repeat it.")
                # Block: Warning and reset product
                self.product_id = False
                return {'warning': {
                    'title': _("Duplicate Blocked"),
                    'message': msg,
                }}
            elif policy == 'warning':
                return {'warning': {
                    'title': _("Duplicate Warning"),
                    'message': msg,
                }}
