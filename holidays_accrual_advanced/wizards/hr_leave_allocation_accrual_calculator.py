from datetime import datetime
from odoo import api, fields, models


class HrLeaveAllocationAccrualBalanceCalculator(models.TransientModel):
    _name = 'hr.leave.allocation.accrual.calculator'
    _description = 'HR Leave Allocation Accrual Calculator'

    date = fields.Date(
        string='Date',
        required=True,
        help='Target date for the balance projection. The system calculates '
             'what the accrual balance would be as of this date.',
    )
    accruement_ids = fields.One2many(
        string='Accruements',
        comodel_name=(
            'hr.leave.allocation.accrual.calculator.accruement'
        ),
        inverse_name='calculator_id',
        readonly=True,
    )
    accrued = fields.Float(
        string='Accrued',
        readonly=True,
        help='Total number of days accrued as of the selected date, '
             'after all limits have been applied.',
    )
    balance = fields.Float(
        string='Balance',
        readonly=True,
        help='Net balance available as of the selected date, '
             'accounting for accruals and any leave consumption.',
    )

    @api.onchange('date')
    def _onchange(self):
        self._recalculate()

    def _recalculate(self):
        self.ensure_one()

        if not self.date:
            self.balance = 0.0
            self.accruement_ids = [(5, False, False)]
            return

        HrLeaveAllocation = self.env['hr.leave.allocation']
        leave_allocation = HrLeaveAllocation.browse(
            self.env.context.get('active_id')
        )

        accruements, accrued = leave_allocation._calculate_accrued_amount(
            datetime.combine(self.date, datetime.min.time()),
        )

        balance = 0.0
        accruement_ids = [(5, False, False)]
        for accruement in accruements:
            balance += accruement.days_accrued
            accruement_ids.append((0, 0, {
                'days_accrued': accruement.days_accrued,
                'accrued_on': accruement.accrued_on,
                'reason': accruement.reason,
            }))

        self.accrued = accrued
        self.balance = balance
        self.accruement_ids = accruement_ids
