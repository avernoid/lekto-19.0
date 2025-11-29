from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockBatchSpreadsheetTemplate(models.Model):
    _name = 'stock.batch.spreadsheet.template'
    _description = 'Batch Spreadsheet Template'

    name = fields.Char(required=True, translate=True)
    spreadsheet_id = fields.Many2one(
        'stock.batch.spreadsheet',
        string='Spreadsheet Template',
        required=False,
        ondelete='cascade',
        domain="[('batch_id', '=', False)]"
    )
    picking_type_ids = fields.Many2many('stock.picking.type', string='Operation Types', help='Operation types that can use this template.')

    @api.model
    def create(self, vals):
        return super().create(vals)

    def action_create_spreadsheet(self):
        self.ensure_one()
        if self.spreadsheet_id:
            raise UserError(_("This template already has a spreadsheet. Use 'Edit Spreadsheet' to modify it."))
        
        # Create a new blank spreadsheet
        spreadsheet = self.env['stock.batch.spreadsheet'].create({
            'name': _('Template: %s') % self.name,
        })
        
        self.spreadsheet_id = spreadsheet.id
        
        return self.action_open_spreadsheet()

    def action_open_spreadsheet(self):
        self.ensure_one()
        if not self.spreadsheet_id:
            raise UserError(_("Please select a Spreadsheet Template first."))
            
        return self.spreadsheet_id.action_open_spreadsheet()
