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
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company,
        help="Company whose valuation was recalculated. Without it an audit "
             "trail is visible across companies that never took part in it.")
    mode = fields.Selection(
        [('adjust', 'Adjustment (additive)'), ('restate', 'Restate values')],
        string='Mode', readonly=True, default='adjust',
        help="Adjustment records the correction beside the native value and is "
             "reversible. Restate overwrites stock move values.")
    
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
    company_id = fields.Many2one('res.company', related='audit_id.company_id', store=True)
    detail_ids = fields.One2many(
        'stock.valuation.recalc.audit.detail', 'audit_line_id', string='Movements',
        help="What each affected movement was worth before and after. Without "
             "this the operation cannot be undone and nothing proves to an "
             "auditor what actually changed.")


class StockValuationAuditDetail(models.Model):
    _name = 'stock.valuation.recalc.audit.detail'
    _description = 'Audit Detail per Movement'

    audit_line_id = fields.Many2one(
        'stock.valuation.recalc.audit.line', string='Audit Line',
        ondelete='cascade', required=True, index=True,
        help="The audited product line this movement belongs to.")
    move_id = fields.Many2one(
        'stock.move', string='Stock Move', index='btree_not_null',
        help="The stock movement that was corrected. Empty when the row "
             "records a deleted valuation anchor instead.")
    previous_value = fields.Monetary(
        string='Value Before', currency_field='currency_id',
        help="What the movement was worth before the recalculation. This is "
             "the figure to restore in order to undo it.")
    new_value = fields.Monetary(
        string='Value After', currency_field='currency_id',
        help="What the movement is worth after the recalculation. In "
             "adjustment mode the native value is untouched and the difference "
             "is carried by the Kardex adjustment column instead.")
    deleted_product_value_date = fields.Datetime(
        string='Deleted Anchor Date',
        help="Set when the row records a product.value anchor removed by a "
             "restatement, rather than a movement correction.")
    currency_id = fields.Many2one(
        'res.currency', related='audit_line_id.currency_id')
