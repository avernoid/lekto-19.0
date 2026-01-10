from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    duplicate_warning_banner = fields.Html(
        compute='_compute_duplicate_warning_banner',
        string='Duplicate Warning'
    )

    def _get_duplicate_lines(self, moves):
        """
        Helper to detect duplicate (product_id, description_picking) pairs.
        Returns a list of strings representing the duplicates.
        """
        seen = set()
        duplicates = set()
        
        # We process moves to find duplicates based on Product and Description
        for move in moves:
            if not move.product_id:
                continue
                
            # Use a tuple of (product_id.id, description_picking) as key
            # description_picking might be False/None, normalize to empty string if needed for consistent comparison,
            # but usually in Odoo it's a string.
            desc = move.description_picking or ''
            key = (move.product_id.id, desc)
            
            if key in seen:
                # Format the duplicate name for display
                name = move.product_id.display_name
                if desc:
                    name += f" ({desc})"
                duplicates.add(name)
            else:
                seen.add(key)
                
        return list(duplicates)

    @api.depends('move_ids.product_id', 'move_ids.description_picking', 'move_ids.state', 
                 'move_ids_without_package.product_id', 'move_ids_without_package.description_picking', 'move_ids_without_package.state',
                 'picking_type_id.duplicate_product_policy')
    def _compute_duplicate_warning_banner(self):
        for picking in self:
            picking.duplicate_warning_banner = False
            
            # Check policy availability and if it's relevant (warning or block)
            if not picking.picking_type_id or picking.picking_type_id.duplicate_product_policy == 'allow':
                continue

            # Check duplicates
            # We filter out cancelled/done moves as per requirements
            all_moves = picking.move_ids | picking.move_ids_without_package
            moves = all_moves.filtered(lambda m: m.state not in ('cancel', 'done'))
            duplicates = picking._get_duplicate_lines(moves)
            
            if duplicates:
                formatted_list = "<ul>" + "".join([f"<li>{name}</li>" for name in duplicates]) + "</ul>"
                # If block, the banner explains it will block. If warning, it just warns.
                msg_title = _("Duplicate Lines Detected")
                msg_body = _("The following products are duplicated (Same Product + Description):")
                
                picking.duplicate_warning_banner = f"""
                    <div class="alert alert-warning" role="alert">
                        <h4 class="alert-heading">{msg_title}</h4>
                        <p>{msg_body}</p>
                        {formatted_list}
                    </div>
                """

    @api.constrains('move_ids')
    def _check_duplicate_product_policy(self):
        for picking in self:
            if picking.picking_type_id.duplicate_product_policy == 'block':
                moves = picking.move_ids.filtered(lambda m: m.state not in ('cancel', 'done'))
                duplicates = picking._get_duplicate_lines(moves)
                if duplicates:
                    raise ValidationError(_(
                        "You cannot validate this picking because the following products are duplicated:\n%s\n"
                        "Check the Duplicate Product Policy on the Operation Type."
                    ) % "\n".join(duplicates))
