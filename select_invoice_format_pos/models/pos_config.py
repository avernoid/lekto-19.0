from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    invoice_report_id = fields.Many2one(
        comodel_name='ir.actions.report',
        string='Invoice Format',
        domain='[("model", "=", "account.move")]',
        default=lambda self: self.env.ref('account.account_invoices'),
        help="Select the invoice report format to print from the POS receipt screen. "
             "This report will be used when clicking the 'Electronic Receipt' button after completing a sale. "
             "You can choose any invoice report configured in your system (standard or custom). "
             "If left empty, the system will use Odoo's default 'Invoices' report. "
             "The selected format applies to all sessions of this POS configuration."
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if params and 'invoice_report_id' not in params:
            params.append('invoice_report_id')
        return params
