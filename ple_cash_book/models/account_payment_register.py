from odoo import fields, models, api


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    inv = fields.Boolean(
        string="Show Payment Method",
        compute='_compute_inv',
        help="Technical field that controls the visibility of the Payment Method (Medio de Pago) field. "
             "When True (journal is not cash type), the payment method selector is shown. "
             "When False (cash journal), it is hidden since cash payments default to code '003'.",
    )

    def _get_default_means_payment(self):
        means_payment_id = self.env['payment.methods.codes'].search([('code', '=', '003')], limit=1)
        if means_payment_id:
            return means_payment_id.id

    @api.depends('journal_id')
    def _compute_inv(self):
        for rec in self:
            rec.inv = rec.journal_id.type != 'cash'

    means_payment_id = fields.Many2one(
        comodel_name='payment.methods.codes',
        string="Payment Method (Bank Book)",
        help="SUNAT payment method code used in the PLE Bank Book report (TXT 1.2). "
             "Defaults to code '003' (bank transfer). This field only appears when "
             "the selected journal is of bank type. For cash journals, code '003' is used automatically.",
        default=lambda self: self._get_default_means_payment(),
    )

    def _create_payment_vals_from_batch(self, batch_result):
        values = super()._create_payment_vals_from_batch(batch_result)
        values = {'means_payment_id': self._context.get('means_payment_id'), **values}
        return values

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['means_payment_id'] = self.means_payment_id.id
        return payment_vals
