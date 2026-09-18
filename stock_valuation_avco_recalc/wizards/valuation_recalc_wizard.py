from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ValuationRecalcWizard(models.TransientModel):
    _name = 'stock.valuation.recalc.wizard'
    _description = 'Valuation Rebuild Wizard'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
        help="Company whose valuation is rebuilt. The movements and the costing method are read in it.")
    date = fields.Date(
        string='Known From', required=True, default=fields.Date.context_today,
        help="Date from which the rebuilt values count as known. Every period before it keeps the "
             "values it was reported with; the differences print in the period of this date. It cannot "
             "fall inside a locked period.")
    line_ids = fields.One2many(
        'stock.valuation.recalc.line', 'wizard_id', string='Products to Rebuild',
        help="Products of the selected movements.")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        if context.get('active_model') == 'stock.move' and context.get('active_ids'):
            products = self.env['stock.move'].browse(context['active_ids']).product_id.filtered('is_storable')
            res['line_ids'] = [(0, 0, {'product_id': product.id}) for product in products]
        return res

    @api.constrains('date', 'company_id')
    def _check_date_not_locked(self):
        for wizard in self:
            company = wizard.company_id
            lock = max(filter(None, (company.fiscalyear_lock_date, company.hard_lock_date)), default=None)
            if lock and wizard.date <= lock:
                raise ValidationError(_(
                    "The rebuilt values cannot be dated on %(date)s: the accounting is locked until %(lock)s. "
                    "A locked period must keep the values it was closed with.",
                    date=wizard.date, lock=lock))

    def action_confirm_recalc(self):
        """Rebuild each product and keep the record of what changed.

        The audit models are deliberately non-writable (perm_write=0 for everybody), so the header and
        its lines are born in a single create.
        """
        self.ensure_one()
        audit_lines = []
        for line in self.line_ids:
            result = self.env['stock.move']._valuation_rebuild(line.product_id, self.company_id, self.date)
            audit_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'recalc_start_date': fields.Datetime.to_datetime(self.date),
                'moves_affected_count': result['moves_count'],
                'value_correction_total': result['total_correction'],
                'detail_ids': result['details'],
            }))
        audit = self.env['stock.valuation.recalc.audit'].create({
            'company_id': self.company_id.id,
            'mode': 'rebuild',
            'log_notes': _("Rebuild of %(count)s products in %(company)s, known from %(date)s. No journal "
                           "entry was posted.", count=len(self.line_ids),
                           company=self.company_id.display_name, date=self.date),
            'audit_lines': audit_lines,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Valuation Rebuild Audit'),
            'res_model': 'stock.valuation.recalc.audit',
            'res_id': audit.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ValuationRecalcLine(models.TransientModel):
    _name = 'stock.valuation.recalc.line'
    _description = 'Line for Valuation Rebuild Wizard'

    wizard_id = fields.Many2one('stock.valuation.recalc.wizard')
    product_id = fields.Many2one('product.product', required=True)
