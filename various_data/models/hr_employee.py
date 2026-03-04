from odoo import api, fields, models
from odoo.exceptions import ValidationError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    pension_sctr = fields.Boolean(
        string='SCTR',
        help="Check this box if the employee is subject to SCTR (Complementary High Risk Work Insurance).",
        groups="hr.group_hr_user"
    )

    sctr_id = fields.Many2many(
        comodel_name='various.data.sctr',
        relation='hr_employee_sctr_rel',
        column1='employee_id',
        column2='sctr_id',
        string='SCTR Policy',
        help="Select the specific SCTR policy applicable to this employee for the correct calculation of risk insurance contributions.",
        groups="hr.group_hr_user"
    )

    sctr_name = fields.Char(
        string='Policy Name',
        help="Displays the name of the assigned SCTR policy.",
        compute='_compute_sctr_name',
        store=False
    )

    @api.depends('sctr_id')
    def _compute_sctr_name(self):
        for rec in self:
            rec.sctr_name = rec.sctr_id[:1].sctr_name or ''

    @api.constrains('sctr_id')
    def _check_single_sctr(self):
        for rec in self:
            if len(rec.sctr_id) > 1:
                raise ValidationError("Solo se permite seleccionar una póliza SCTR por empleado.")
