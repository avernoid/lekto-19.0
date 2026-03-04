from odoo import api, fields, models


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    schedule_pay_conditions = fields.Many2one(
        comodel_name='payment.period',
        string='Payment Period',
        default=lambda self: self.env.ref('payment_conditions.payment_period_1', False),
        help="Indicates the payment frequency associated with this salary structure (e.g., Monthly, Biweekly). "
             "This value is used to classify the structure and may affect payroll processing calculations. "
             "Defaults to the period defined on the salary structure type."
    )

    @api.depends('type_id')
    def _compute_schedule_pay_conditions(self):
        for structure in self:
            if not structure.type_id:
                structure.schedule_pay_conditions = self.env.ref('payment_conditions.payment_period_1', False)
            elif not structure.schedule_pay_conditions:
                structure.schedule_pay_conditions = structure.type_id.default_schedule_pay_conditions