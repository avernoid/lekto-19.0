from odoo import models, fields


class HrLeaveAllocationAccruement(models.Model):
    """Describes an alteration to the accrual leave balance in order to provide
    definitive explanation how the actual balance was changing over the time.
    """

    _name = 'hr.leave.allocation.accruement'
    _description = 'Leaves Allocation Accruement'

    leave_allocation_id = fields.Many2one(
        string='Leave Allocation',
        comodel_name='hr.leave.allocation',
        help='The accrual allocation this entry belongs to.',
    )
    days_accrued = fields.Float(
        string='Number of Days',
        readonly=True,
        required=True,
        help='Number of days added (positive) or lost (negative) in this entry. '
             'Negative values indicate losses due to limit enforcement.',
    )
    accrued_on = fields.Date(
        string='Accruement Date',
        readonly=True,
        required=True,
        help='The date when this balance change was applied.',
    )
    reason = fields.Char(
        string='Reason',
        readonly=True,
        required=True,
        help='Descriptive reason for this entry, e.g. "Prorate accruement for X of Y days" '
             'or "Loss due to accumulation limit".',
    )
