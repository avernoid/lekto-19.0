from odoo import models, fields, api
from odoo.exceptions import ValidationError

class EpsEmployee(models.Model):
    _inherit = 'hr.employee'

    exists_eps = fields.Boolean(
        string='Exists EPS',
        groups="hr.group_hr_user",
        help="Check this box if the employee is enrolled in an EPS plan."
    )
    management_eps = fields.Many2one(
        comodel_name='eps.management',
        string='EPS Policy',
        groups="hr.group_hr_user",
        help="Select the active EPS policy for this employee."
    )

    def update_management_eps_date(self):
        current_date = fields.Date.today()
        eps_existents = self.env['eps.management'].search([
            ('employeer_ids', 'in', self.id),
            ('star_date', '<=', current_date),
            ('finish_date', '>=', current_date)
        ])
        if eps_existents:
            self.management_eps = eps_existents[0].id
            self.exists_eps = True
        else:
            self.exists_eps = False
            self.management_eps = False

    @api.onchange('exists_eps')
    def _onchange_exists_eps(self):
        if not self.exists_eps:
            self.management_eps = False

    @api.model
    def create(self, values):
        employee = super(EpsEmployee, self).create(values)
        if employee.exists_eps and employee.management_eps:
            employee.management_eps.write({'employeer_ids': [(4, employee.id)]})
        return employee

    def write(self, values):
        # Guard against mutual recursion between hr.employee.write and
        # eps.management.write (which calls back hr.employee.write).
        if self.env.context.get('_eps_sync_in_progress'):
            return super(EpsEmployee, self).write(values)

        # Capture previous policies before update (per employee)
        prev_policies = {emp.id: emp.management_eps for emp in self}
        result = super(EpsEmployee, self).write(values)

        if 'exists_eps' in values or 'management_eps' in values:
            for employee in self:
                prev_policy = prev_policies[employee.id]
                if not employee.exists_eps or not employee.management_eps:
                    # EPS disabled or policy cleared — remove from old policy
                    if prev_policy:
                        prev_policy.with_context(_eps_sync_in_progress=True).write(
                            {'employeer_ids': [(3, employee.id)]}
                        )
                    # Use super() directly to avoid re-triggering this hook
                    super(EpsEmployee, employee).write(
                        {'management_eps': False, 'exists_eps': False}
                    )
                elif employee.exists_eps and employee.management_eps:
                    # If the policy changed, remove from the previous one first
                    if prev_policy and prev_policy != employee.management_eps:
                        prev_policy.with_context(_eps_sync_in_progress=True).write(
                            {'employeer_ids': [(3, employee.id)]}
                        )
                    employee.management_eps.with_context(_eps_sync_in_progress=True).write(
                        {'employeer_ids': [(4, employee.id)]}
                    )
        return result
