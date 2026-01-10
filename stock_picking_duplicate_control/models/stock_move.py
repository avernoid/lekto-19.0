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
        existing_moves = self.picking_id.move_ids
        
        count = 0
        for move in existing_moves:
            # Skip if it's the exact same record in memory (comparing NewIds works effectively in Odoo JS context usually, 
            # but in python onchange, self is a virtual record)
            # A robust way is to check how many times this key appears.
            
            # Note: 'move' here comes from the picking's one2many.
            if move.product_id == self.product_id and (move.description_picking or '') == current_desc:
                count += 1
        
        # If we are creating a new line, it might not be in existing_moves yet, or it might be.
        # If we are editing, it is definitely in there.
        # The 'self' is the record being edited.
        
        # If count > 1, strictly duplicate. 
        # But wait, 'self' might NOT be in existing_moves yet if it's a fresh creation line in the UI before "Save & New" or similar.
        # However, usually the Onchange triggers on the single line form or editable list.
        
        # Let's try a simpler approach: Check if ANY OTHER line has same tuple.
        # We can try to match by ID if origin exists, or just count occurrences.
        
        # If I am just typing product_id, and not added to the list yet?
        # Onchange happens on the record.
        
        # Let's count how many lines in picking match this criteria.
        # If self is in picking.move_ids_without_package, we expect count >= 1 (itself).
        # If self is NOT in picking.move_ids_without_package (weird, but possible if completely new), count == 0 is fine.
        
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
