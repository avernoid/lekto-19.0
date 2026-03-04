from odoo import fields, models


class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    default_schedule_pay_conditions = fields.Many2one(
        comodel_name='payment.period',
        string='Default Payment Period',
        default=lambda self: self.env.ref('payment_conditions.payment_period_1', False),
        help="Defines the default payment frequency for this salary structure type (e.g., Monthly, Biweekly). "
             "When a new salary structure is created under this type and no specific period is set, "
             "this value will be used as the default payment period for payroll processing."
    )
