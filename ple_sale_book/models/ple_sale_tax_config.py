from odoo import models, fields, api

class PleSaleTaxConfig(models.Model):
    _name = 'ple.sale.tax.config'
    _description = 'PLE Sale Tax Configuration'
    _order = 'sequence, id'

    name = fields.Char(string='Description', required=True, help="E.g. IGV 18% - Base")
    sequence = fields.Integer(default=10)
    
    # Tax Identification
    tax_prefix = fields.Char(string='Prefix', default='l10n_pe', required=True, help="XML ID Prefix. Default: l10n_pe")
    tax_code = fields.Char(string='Tax Code (Suffix)', required=True, help="XML ID Suffix. E.g. sale_tax_igv_18")
    
    # Rule Type
    repartition_type = fields.Selection([
        ('base', 'Base'),
        ('tax', 'Tax')
    ], string='Repartition Type', required=True, default='base')
    
    # Target Tags
    tag_invoice_id = fields.Many2one('account.account.tag', string='Invoice Tag', help="Tag for Sales Invoices")
    tag_refund_id = fields.Many2one('account.account.tag', string='Refund Tag', help="Tag for Credit Notes (Refunds)")
    
    notes = fields.Text(string='Notes')

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.name} ({rec.tax_code})"
            result.append((rec.id, name))
        return result

    def action_update_tags_wizard(self):
        """ Opens the wizard with this record pre-selected """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Update PLE Tags',
            'res_model': 'ple.update.tags.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_config_ids': [self.id],
            }
        }
