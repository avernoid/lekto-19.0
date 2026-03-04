from odoo import fields, models


class PaymentType(models.Model):
    _name = 'payment.type'
    _description = 'Payment Type'

    code = fields.Char(
        string='Code',
        help="Short identifier for this payment type (e.g., TRA for Bank Transfer, EFE for Cash). "
             "Used in reports and payroll exports to reference the payment modality."
    )
    payment_description = fields.Char(
        string='Description',
        help="Full descriptive name of the payment type (e.g., 'Bank Transfer', 'Cash', 'Check'). "
             "This text is shown in configuration menus and contract forms."
    )
    name = fields.Char(
        string='Abbreviation',
        help="Short abbreviation displayed in selectors and contract forms (e.g., TRA, EFE, CHQ). "
             "This is the value visible to users when selecting a payment type on a contract."
    )
