from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('move_id.stock_move_ids', 'move_id.invoice_user_id', 'move_id.user_id', 'journal_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()

    def _get_analytic_distribution_arguments(self, root_plans):
        """ Returns the arguments to matching the distribution models. """
        self.ensure_one()
        args = super()._get_analytic_distribution_arguments(root_plans)
        args.update({
            'origin_warehouse_id': (self.move_id.stock_move_ids[:1].picking_type_id.warehouse_id.id if self.move_id.stock_move_ids else False),
            'origin_location_id': (self.move_id.stock_move_ids[:1].location_id.id if self.move_id.stock_move_ids else False),
            'dest_location_id': (self.move_id.stock_move_ids[:1].location_dest_id.id if self.move_id.stock_move_ids else False),
            'invoice_user_id': self.move_id.invoice_user_id.id,
            'user_id': self.move_id.user_id.id,
            'journal_id': self.journal_id.id,
        })
        return args

