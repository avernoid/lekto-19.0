from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_automatic_print_electronic_invoice = fields.Boolean(
        related='pos_config_id.automatic_print_electronic_invoice',
        string='Automatic Electronic Invoice Printing',
        readonly=False,
        help='If enabled, the system will automatically trigger the print dialog for the electronic invoice PDF immediately after the POS order is validated.'
    )
    pos_automatic_download_electronic_invoice = fields.Boolean(
        related='pos_config_id.automatic_download_electronic_invoice',
        string='Automatic Electronic Invoice Download',
        readonly=False,
        help='If enabled, the browser will automatically initiate a download of the electronic invoice PDF once the POS order is validated.'
    )

    @api.onchange('pos_iface_print_auto')
    def _onchange_pos_iface_print_auto(self):
        if self.pos_iface_print_auto:
            self.pos_automatic_print_electronic_invoice = False

    @api.onchange('pos_automatic_print_electronic_invoice')
    def _onchange_pos_automatic_print_electronic_invoice(self):
        if self.pos_automatic_print_electronic_invoice:
            self.pos_iface_print_auto = False
