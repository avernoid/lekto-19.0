from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ValuationRecalcWizard(models.TransientModel):
    _name = 'stock.valuation.recalc.wizard'
    _description = 'Valuation Recalculation Wizard'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
        help="Company whose valuation is recalculated. Everything -- the moves "
             "swept, the opening balance and the cost method check -- is scoped "
             "to it.")
    mode = fields.Selection(
        [('adjust', 'Adjustment (additive, reversible)'),
         ('restate', 'Restate movement values')],
        string='Mode', required=True, default='adjust',
        help="Adjustment records the correction beside the native value, so the "
             "original survives and the operation can be undone. Restate "
             "overwrites the stored value of each movement: use it only when "
             "the underlying data is genuinely corrupt, because it rewrites "
             "history that may already have been declared.")
    line_ids = fields.One2many('stock.valuation.recalc.line', 'wizard_id', string='Products to Recalculate', help="Review and adjust the initial balances for each product before confirming.")
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        active_ids = context.get('active_ids')
        active_model = context.get('active_model')

        company = self.env['res.company'].browse(res.get('company_id')) or self.env.company
        if active_model == 'stock.move' and active_ids:
            moves = self.env['stock.move'].browse(active_ids)
            lines_data = []
            
            # Group by Product -> Find Min Date
            product_min_dates = {}
            for move in moves:
                curr_min = product_min_dates.get(move.product_id, move.date)
                if move.date < curr_min:
                    product_min_dates[move.product_id] = move.date
                else:
                    product_min_dates[move.product_id] = curr_min
            
            # Prepare Lines using SQL Genesis
            for product, min_date in product_min_dates.items():
                if product.with_company(company).cost_method != 'average':
                    # Skip or Raise? Better to Raise to warn the user specifically.
                    # Or maybe just skip and show a warning message?
                    # The user asked "What happens if I select...", leading to disaster.
                    # Let's BLOCK it to be safe.
                    raise ValidationError(_(
                        "Product '%s' uses '%s' costing method. "
                        "This Fix is strictly for Average Cost (AVCO) products only."
                    ) % (product.display_name, product.cost_method))

                # --- Find Oldest Remaining Layer (Python Side) ---
                # Odoo 19 'remaining_qty' is not searchable (computed non-stored).
                # We fetch prior incoming moves and filter in Python to find the oldest
                # active layer, respecting the requirement to start from the oldest active stock.
                prior_candidates = self.env['stock.move'].search([
                    ('product_id', '=', product.id),
                    ('company_id', '=', company.id),
                    ('is_in', '=', True),
                    ('date', '<', min_date),
                    ('state', '=', 'done')
                ], order='date asc')

                for move in prior_candidates:
                    if move.remaining_qty > 0:
                        min_date = move.date  # oldest active layer
                        break

                # Genesis: computed once, with the definitive min_date.
                init_qty, init_val = self.env['stock.move']._get_historical_balance_at_date(
                    product.id, min_date, company=company,
                    mode=res.get('mode') or 'adjust')

                lines_data.append((0, 0, {
                    'product_id': product.id,
                    'start_date': min_date,
                    'initial_qty': init_qty,
                    'initial_value': init_val,
                }))
            
            res['line_ids'] = lines_data
            
        return res

    def action_confirm_recalc(self):
        """
        Orchestrates the Recalculation.
        1. Loops lines -> calls force recalculation logic.
        2. Creates the Audit (header + lines) in one write-free create.
        3. Opens Audit View.
        """
        self.ensure_one()

        # The audit models are deliberately non-writable: every ACL declares
        # perm_write=0 so nobody can rewrite the record of their own correction
        # (see test_04_audit_trail_cannot_be_edited_or_deleted). The header and
        # its lines must therefore be born in a SINGLE create. Creating the
        # header first and writing the lines onto it afterwards raised
        # "You are not allowed to modify ... No group currently allows this
        # operation" for every user, administrators included.
        audit_lines = []
        
        for line in self.line_ids:
            # 2. Execute Logic (Calling the logic on stock.move model)
            # We pass the user-edited Initial Qty/Value!
            # 2. Execute Logic (Calling the logic on stock.move model)
            # We pass the user-edited Initial Qty/Value!
            verify_res = self.env['stock.move']._recalculate_valuation_waterfall(
                line.product_id.id,
                line.start_date,
                line.initial_qty,
                line.initial_value,
                new_standard_price=line.new_standard_price,
                company=self.company_id,
                mode=self.mode,
            )
            
            # 3. Create Audit Line
            audit_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'recalc_start_date': line.start_date,
                'moves_affected_count': verify_res['moves_count'],
                'value_correction_total': verify_res['total_correction'],
                'initial_qty_used': line.initial_qty,
                'initial_value_used': line.initial_value,
                'detail_ids': verify_res['details'],
            }))
            
        audit = self.env['stock.valuation.recalc.audit'].create({
            'company_id': self.company_id.id,
            'mode': self.mode,
            'log_notes': f"Batch execution for {len(self.line_ids)} products "
                         f"in {self.company_id.display_name} (mode: {self.mode}).",
            'audit_lines': audit_lines,
        })

        # 4. Open the Audit Log
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recalculation Audit'),
            'res_model': 'stock.valuation.recalc.audit',
            'res_id': audit.id,
            'view_mode': 'form',
            'target': 'current',
        }

class ValuationRecalcLine(models.TransientModel):
    _name = 'stock.valuation.recalc.line'
    _description = 'Line for Recalc Wizard'

    wizard_id = fields.Many2one('stock.valuation.recalc.wizard')
    product_id = fields.Many2one('product.product', readonly=True)
    start_date = fields.Datetime(string='Start From', readonly=True)
    
    # EDITABLE FIELDS ("God Mode")
    initial_qty = fields.Float(string='Initial Qty (Snapshot)', help="Calculated qty just before Start Date. Edit if needed.")
    initial_value = fields.Monetary(string='Initial Value (Snapshot)', currency_field='currency_id', help="Calculated value just before Start Date. Edit if needed.")
    new_standard_price = fields.Float(
        string='New Standard Price',
        help="Restate mode only. Forces the product cost by a direct SQL write "
             "that bypasses Odoo's automatic revaluation. Not available when "
             "adjusting, where the correction is recorded beside the movement "
             "and the product cost is left to the engine.")
    
    currency_id = fields.Many2one('res.currency', related='product_id.currency_id')
