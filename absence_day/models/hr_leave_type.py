from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    code = fields.Char(
        string='Code',
        help="A short internal code for this leave type (e.g., 'PPD' for 'Pending determination'). "
             "Used for identification and payroll integration.",
    )
