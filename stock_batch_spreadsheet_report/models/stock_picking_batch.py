from odoo import models, fields, _
from odoo.exceptions import UserError
import json
import base64
import logging

_logger = logging.getLogger(__name__)

class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    spreadsheet_ids = fields.One2many(
        'stock.batch.spreadsheet',
        'batch_id',
        string='Spreadsheet Reports'
    )
    spreadsheet_id = fields.Many2one(
        'stock.batch.spreadsheet',
        compute='_compute_spreadsheet_id',
    )
    spreadsheet_count = fields.Integer(compute='_compute_spreadsheet_count')

    def _compute_spreadsheet_id(self):
        for batch in self:
            batch.spreadsheet_id = batch.spreadsheet_ids[:1]

    def _compute_spreadsheet_count(self):
        for batch in self:
            batch.spreadsheet_count = len(batch.spreadsheet_ids)

    def action_create_spreadsheet_report(self):
        self.ensure_one()
        
        # If report already exists, open it directly
        if self.spreadsheet_id:
            return self.spreadsheet_id.action_open_spreadsheet()

        # Get template from picking type
        template = self.picking_type_id.batch_spreadsheet_template_id
        if not template:
            raise UserError(_("No Spreadsheet Template configured for this Operation Type."))

        if not template.spreadsheet_id:
            raise UserError(_("The configured template has no linked spreadsheet."))

        # Copy the template spreadsheet and link it to this batch
        new_spreadsheet = template.spreadsheet_id.copy({
            "batch_id": self.id,
            "name": self.name,
        })
        
        return new_spreadsheet.action_open_spreadsheet()

    def action_view_spreadsheet_reports(self):
        self.ensure_one()
        # If there is only one report, open it directly
        if len(self.spreadsheet_ids) == 1:
            return self.spreadsheet_ids[0].action_open_spreadsheet()
            
        return {
            'name': _('Spreadsheet Reports'),
            'domain': [('batch_id', '=', self.id)],
            'res_model': 'stock.batch.spreadsheet',
            'view_mode': 'kanban,tree,form',
            'type': 'ir.actions.act_window',
            'context': {'default_batch_id': self.id},
        }
