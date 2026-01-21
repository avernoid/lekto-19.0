from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_invoice_report_id = fields.Many2one(
        related='pos_config_id.invoice_report_id',
        string='Invoice Format',
        readonly=False,
        help="Choose the invoice report format for this POS. "
             "This format will be used when printing invoices from the POS receipt screen."
    )
