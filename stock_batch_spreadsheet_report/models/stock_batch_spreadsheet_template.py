from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockBatchSpreadsheetTemplate(models.Model):
    _name = 'stock.batch.spreadsheet.template'
    _description = 'Batch Spreadsheet Template'

    name = fields.Char(
        required=True, 
        translate=True,
        help="The name of the template (e.g., 'Delivery Batch Sheet')."
    )
    spreadsheet_id = fields.Many2one(
        'stock.batch.spreadsheet',
        string='Spreadsheet Template',
        required=False,
        ondelete='cascade',
        domain="[('batch_id', '=', False)]",
        help="The actual spreadsheet file that serves as the blueprint. When a report is generated, this spreadsheet is copied."
    )
    picking_type_ids = fields.Many2many(
        'stock.picking.type', 
        string='Operation Types', 
        help='Operation Types (e.g., Pick, Pack, Ship) that can use this template to generate reports.'
    )

    @api.model
    def create(self, vals):
        return super().create(vals)

    def unlink(self):
        spreadsheets = self.mapped('spreadsheet_id')
        res = super().unlink()
        if spreadsheets:
            spreadsheets.unlink()
        return res

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
