from odoo import fields, models


class PaymentPeriod(models.Model):
    _name = 'payment.period'
    _description = 'Payment Period'

    code = fields.Char(
        string='Code',
        help="Short identifier for this payment period (e.g., MEN for Monthly, QUI for Biweekly). "
             "Used in reports and payroll processing to reference the remuneration periodicity."
    )
    payment_description = fields.Char(
        string='Description',
        help="Full descriptive name of the payment period (e.g., 'Monthly', 'Fortnightly'). "
             "This text is shown in configuration menus and reports."
    )
    name = fields.Char(
        string='Abbreviation',
        help="Short abbreviation displayed in selectors and contract forms (e.g., MEN, QUI, SEM). "
             "This is the value visible to users when selecting a payment period on a contract."
    )
