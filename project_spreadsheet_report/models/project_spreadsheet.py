from odoo import models, fields, api, _

class ProjectSpreadsheet(models.Model):
    _name = "project.spreadsheet"
    _inherit = "spreadsheet.mixin"
    _description = "Project Spreadsheet"

    name = fields.Char(required=True, default=lambda self: _('Untitled spreadsheet'))
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    project_id = fields.Many2one("project.project", string="Project", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        spreadsheets = super().create(vals_list)
        for spreadsheet, vals in zip(spreadsheets, vals_list):
            if not spreadsheet.project_id and not ('spreadsheet_binary_data' in vals or 'spreadsheet_data' in vals):
                spreadsheet._dispatch_default_data()
        return spreadsheets

    def _get_spreadsheet_metadata(self, access_token=None):
        data = super()._get_spreadsheet_metadata(access_token)
        if self.project_id:
            data["project_id"] = self.project_id.id
            data["project_display_name"] = self.project_id.display_name
        return data

    def _empty_spreadsheet_data(self):
        data = super()._empty_spreadsheet_data()
        data['globalFilters'] = [{
            'id': 'project_filter_id',
            'type': 'relation',
            'label': _("Project"),
            'modelName': 'project.project',
        }]
        return data

    @api.readonly
    @api.model
    def get_spreadsheets(self, domain=(), offset=0, limit=None):
        from odoo.fields import Domain
        domain = Domain.AND([domain, [("project_id", "=", False)]])
        return super().get_spreadsheets(domain, offset, limit)

    @api.model
    def _get_spreadsheet_selector(self):
        return {
            'model': self._name,
            'display_name': _("Project Templates"),
            'sequence': 30,
            'allow_create': False,
        }

    def _dispatch_default_data(self):
        import json
        self.spreadsheet_data = json.dumps(self._empty_spreadsheet_data())

    def action_open_spreadsheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'action_project_spreadsheet',
            'params': {
                'spreadsheet_id': self.id,
            },
        }
