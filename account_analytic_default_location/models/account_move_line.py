from odoo import models, api
from odoo.tools import frozendict


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    @api.depends('account_id', 'partner_id', 'product_id', 'move_id.stock_move_ids', 'move_id.invoice_user_id', 'move_id.user_id', 'journal_id')
    def _compute_analytic_distribution(self):
        cache = {}
        for line in self:
            if line.display_type != 'product' and line.move_id.is_invoice(include_receipts=True):
                continue

            # 1. Get Distribution from related documents (SO/PO) - Supreme Priority
            related_distribution = line._related_analytic_distribution()
            
            # 2. Odoo Native Behavior: If there's a related distribution, USE IT and STOP.
            # Do NOT merge with default rules. This prevents "Analytic Merging" bugs.
            if related_distribution:
                line.analytic_distribution = related_distribution
                continue

            # 3. Smart Recomputation (Override Protection)
            # Only compute defaults if the field is empty OR if the product changed (standard Odoo)
            # This ensures manual user entries are respected.
            product_changed = line._origin.product_id != line.product_id
            if not line.analytic_distribution or product_changed:
                root_plans = self.env['account.analytic.account'].browse(
                    list({int(account_id) for ids in related_distribution for account_id in ids.split(',')})
                ).exists().root_plan_id

                arguments = frozendict(line._get_analytic_distribution_arguments(root_plans))
                if arguments not in cache:
                    cache[arguments] = self.env['account.analytic.distribution.model']._get_distribution(arguments)
                
                line.analytic_distribution = cache[arguments] or line.analytic_distribution


    def _get_analytic_distribution_arguments(self, root_plans):
        """ Returns the arguments to matching the distribution models. """
        self.ensure_one()
        args = super()._get_analytic_distribution_arguments(root_plans)
        args.update({
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'product_categ_id': self.product_id.categ_id.id,
            'account_prefix': self.account_id.code,
            'origin_warehouse_id': (self.move_id.stock_move_ids[:1].picking_type_id.warehouse_id.id if self.move_id.stock_move_ids else False),
            'origin_location_id': (self.move_id.stock_move_ids[:1].location_id.id if self.move_id.stock_move_ids else False),
            'dest_location_id': (self.move_id.stock_move_ids[:1].location_dest_id.id if self.move_id.stock_move_ids else False),
            'invoice_user_id': self.move_id.invoice_user_id.id,
            'user_id': self.move_id.user_id.id,
            'journal_id': self.journal_id.id,
        })

        return args

