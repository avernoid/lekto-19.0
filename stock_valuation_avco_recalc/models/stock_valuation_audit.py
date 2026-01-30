from odoo import models, fields, api

class StockValuationAudit(models.Model):
    _name = 'stock.valuation.recalc.audit'
    _description = 'Stock Valuation Recalculation Audit'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', default='New', readonly=True, help="Unique reference for this audit log.")
    user_id = fields.Many2one('res.users', string='Executed By', default=lambda self: self.env.user, readonly=True, help="The user who triggered the recalculation.")
    execution_date = fields.Datetime(string='Execution Date', default=fields.Datetime.now, readonly=True, help="Timestamp when the recalculation was performed.")
    audit_lines = fields.One2many('stock.valuation.recalc.audit.line', 'audit_id', string='Product Details', help="Detailed breakdown of recalculation results per product.")
    log_notes = fields.Text(string='Execution Summary', readonly=True, help="System notes summarizing the batch execution scope.")
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.valuation.recalc.audit') or 'AUDIT/0000'
        return super().create(vals_list)

class StockValuationAuditLine(models.Model):
    _name = 'stock.valuation.recalc.audit.line'
    _description = 'Audit Line Detail'

    audit_id = fields.Many2one('stock.valuation.recalc.audit', string='Audit Reference', ondelete='cascade', help="Parent Audit Log.")
    product_id = fields.Many2one('product.product', string='Product', required=True, help="The product being recalculated.")
    recalc_start_date = fields.Datetime(string='Recalc. Start Date', help="The historic date from which the recalculation started.")
    moves_affected_count = fields.Integer(string='Moves Affected', help="Number of stock moves that required cost adjustment downstream.")
    value_correction_total = fields.Monetary(string='Total Corrected Value', currency_field='currency_id', help="Total monetary difference applied across all affected moves.")
    currency_id = fields.Many2one('res.currency', related='product_id.currency_id')
    initial_qty_used = fields.Float(string='Started with Qty', help="The quantity balance used as the starting point (Snapshot).")
    initial_value_used = fields.Monetary(string='Started with Value', currency_field='currency_id', help="The valuation balance used as the starting point (Snapshot).")
