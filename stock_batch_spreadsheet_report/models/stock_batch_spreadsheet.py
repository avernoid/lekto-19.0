from odoo import api, fields, models, _


class StockBatchSpreadsheet(models.Model):
    _name = 'stock.batch.spreadsheet'
    _inherit = ['spreadsheet.mixin']
    _description = 'Stock Batch Spreadsheet'

    name = fields.Char(required=True, default=lambda self: _('Untitled spreadsheet'))
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    batch_id = fields.Many2one('stock.picking.batch', index='btree_not_null', ondelete='cascade')

    def get_formview_action(self, access_uid=None):
        return self.action_open_spreadsheet()

    @api.model_create_multi
    def create(self, vals_list):
        spreadsheets = super().create(vals_list)
        for spreadsheet, vals in zip(spreadsheets, vals_list):
            if not spreadsheet.batch_id and not ('spreadsheet_binary_data' in vals or 'spreadsheet_data' in vals):
                spreadsheet._dispatch_default_data()
        return spreadsheets

    def action_open_spreadsheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'action_stock_batch_spreadsheet',
            'params': {
                'spreadsheet_id': self.id,
            },
        }

    def _get_spreadsheet_metadata(self, access_token=None):
        data = super()._get_spreadsheet_metadata(access_token)
        data["batch_id"] = self.batch_id.id
        data["batch_display_name"] = self.batch_id.display_name
        return data

    def _empty_spreadsheet_data(self):
        data = super()._empty_spreadsheet_data()
        data['globalFilters'] = [
            {
                'id': 'batch_filter_id',
                'type': 'relation',
                'label': _("Batch Picking"),
                'modelName': 'stock.picking.batch',
            }
        ]
        return data

    def _dispatch_default_data(self):
        """Override if you want to insert default data when creating an empty spreadsheet"""
        pass

    @api.readonly
    @api.model
    def get_spreadsheets(self, domain=(), offset=0, limit=None):
        from odoo.fields import Domain
        domain = Domain.AND([domain, [("batch_id", "=", False)]])
        return super().get_spreadsheets(domain, offset, limit)

    @api.model
    def _get_spreadsheet_selector(self):
        return {
            'model': self._name,
            'display_name': _("Batch Picking Templates"),
            'sequence': 30,
            'allow_create': False,
        }
