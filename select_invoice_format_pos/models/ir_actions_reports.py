from odoo import api, models


class IrActionsReport(models.Model):
    _name = 'ir.actions.report'
    _inherit = ['ir.actions.report', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['type']
