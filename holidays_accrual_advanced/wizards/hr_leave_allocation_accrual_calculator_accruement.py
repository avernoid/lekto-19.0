from datetime import datetime
from odoo import api, fields, models


class HrLeaveAllocationAccrualCalculatorAccruement(models.TransientModel):
    _name = 'hr.leave.allocation.accrual.calculator.accruement'
    _description = 'HR Leave Allocation Accrual Calculator Accruement'

    calculator_id = fields.Many2one(
        string='Calculator',
        comodel_name='hr.leave.allocation.accrual.calculator',
        help='The calculator wizard this entry belongs to.',
    )
    days_accrued = fields.Float(
        string='Number of Days',
        readonly=True,
        required=True,
        help='Number of days added or lost in this projected entry.',
    )
    accrued_on = fields.Date(
        string='Accruement Date',
        readonly=True,
        required=True,
        help='The projected date for this accruement entry.',
    )
    reason = fields.Char(
        string='Reason',
        readonly=True,
        required=True,
        help='Descriptive reason for this projected entry.',
    )