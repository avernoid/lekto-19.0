from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    automatic_print_electronic_invoice = fields.Boolean(
        string='Automatic Electronic Invoice Printing',
        help='If enabled, the system will automatically trigger the print dialog for the electronic invoice PDF immediately after the POS order is validated.'
    )
    automatic_download_electronic_invoice = fields.Boolean(
        string='Automatic Electronic Invoice Download',
        help='If enabled, the browser will automatically initiate a download of the electronic invoice PDF once the POS order is validated.'
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        fields_to_add = ['trusted_config_ids', 'automatic_print_electronic_invoice', 'automatic_download_electronic_invoice']
        if isinstance(params, list) and params:
            for field in fields_to_add:
                if field not in params:
                    params.append(field)
        return params
