from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    special_situation_id = fields.Many2one(
        related="version_id.special_situation_id",
        inherited=True,
        readonly=False,
        string="Special Situation",
        groups="hr.group_hr_manager",
        help="Indicates the employee's special employment situation as required by labor regulations "
             "(e.g., Maternity Leave, Disability, Micro-enterprise regime). "
             "This field is linked to the active contract version and is only visible to HR Managers. "
             "Setting this field will update the contract version record accordingly."
    )

    payment_type_id = fields.Many2one(
        'payment.type',
        related='version_id.payment_type_id',
        inherited=True,
        readonly=False,
        string="Salary Payment Method",
        groups="hr.group_hr_manager",
        help="Specifies how the employee's salary is paid (e.g., Bank Transfer, Cash, Check). "
             "This field is linked to the active contract version and is only visible to HR Managers. "
             "Setting this field will update the contract version record accordingly."
    )
    variable_payment_id = fields.Many2one(
        'variable.payment',
        related='version_id.variable_payment_id',
        inherited=True,
        readonly=False,
        string="Variable Remuneration",
        groups="hr.group_hr_manager",
        help="Classifies the employee's variable remuneration scheme (e.g., Commission-based, Bonus-based). "
             "This field is linked to the active contract version and is only visible to HR Managers. "
             "Setting this field will update the contract version record accordingly."
    )

class HrContractVersion(models.Model):
    _inherit = 'hr.version'

    special_situation_id = fields.Many2one(
        'special.situation',
        string="Special Situation",
        readonly=False,
        help="Indicates the employee's special employment situation as required by labor regulations "
             "(e.g., Maternity Leave, Disability, Micro-enterprise regime). "
             "This classification is used in legal payroll reports and may affect benefit calculations."
    )
    payment_type_id = fields.Many2one(
        'payment.type',
        string="Salary Payment Method",
        readonly=False,
        help="Specifies by which method the employee's salary is disbursed (e.g., Bank Transfer, Cash, Check). "
             "This information is used in payroll reports and payment processing workflows."
    )
    variable_payment_id = fields.Many2one(
        'variable.payment',
        string="Variable Remuneration",
        readonly=False,
        help="Classifies the employee's variable remuneration scheme (e.g., Commission-based, Bonus-based). "
             "Employees with variable pay components must be classified here so that payroll can apply "
             "the correct computation rules for bonuses and commissions."
    )

    def _get_whitelist_fields_from_template(cls):
        fields = super()._get_whitelist_fields_from_template()
        fields += [
            'special_situation_id',
            'payment_type_id',
            'variable_payment_id',
        ]
        return fields