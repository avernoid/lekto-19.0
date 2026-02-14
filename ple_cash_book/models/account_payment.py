from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_default_means_payment(self):
        means_payment_id = self.env['payment.methods.codes'].search([('code', '=', '003')], limit=1)
        if means_payment_id:
            return means_payment_id.id

    means_payment_id = fields.Many2one(
        comodel_name='payment.methods.codes',
        string="Payment Method (Bank Book)",
        help="SUNAT payment method code used in the PLE Bank Book report (TXT 1.2). "
             "Defaults to code '003' (bank transfer). Select the appropriate method "
             "matching how this payment was made (e.g., check, wire transfer, deposit).",
        default=lambda self: self._get_default_means_payment(),
    )