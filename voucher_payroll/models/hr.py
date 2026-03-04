from odoo import models, fields, api


class HrSalaryRuleCategory(models.Model):
    _inherit = 'hr.salary.rule.category'

    invoice_position = fields.Selection(
        string='Voucher Position',
        help=(
            "Determines the column in which this salary rule category appears on the printed pay slip voucher. "
            "Select 'Position 1' for Earnings (left column), 'Position 2' for Deductions (center column), "
            "or 'Position 3' for Other items (right column). "
            "Only rules with 'Appears on Payslip' enabled are included in the layout."
        ),
        selection=[
            ("pos_1", "Position 1 (Earnings)"),
            ("pos_2", "Position 2 (Deductions)"),
            ("pos_3", "Position 3 (Others)")
        ],
        default="pos_1"
    )


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hiden_overtime = fields.Boolean(
        string='Hide Overtime on Voucher',
        help=(
            "When enabled, overtime-coded worked-day entries are excluded from this employee's printed pay slip voucher. "
            "Regular WORK1 entries without overtime codes will still appear. "
            "Overtime codes filtered out include: HNT_001, WORKN, 27, HE_100, HE_035, HEA_035, HE_025, HEA_025. "
            "Use this setting for employees whose voucher should display only standard working hours."
        )
    )
