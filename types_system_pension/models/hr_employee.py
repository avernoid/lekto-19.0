from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    cuspp = fields.Char(
        string='CUSPP Code',
        groups="hr.group_hr_user",
        help="Unique code assigned to AFP affiliates by the AFP system (Código Único de Sistema Privado de Pensiones). "
             "This code is required for electronic filings (PLAME/T-Registro) when the employee is affiliated with an AFP. "
             "Leave empty for employees enrolled in the SNP (ONP)."
    )
    is_cuspp = fields.Boolean(
        string='CUSPP Active',
        compute='_compute_is_cuspp',
        store=True,
        groups="hr.group_hr_user",
        help="Automatically set to True when the employee's assigned pension system requires a CUSPP code. "
             "This field is read-only and computed automatically based on the Pension System configuration. "
             "If True, the CUSPP Code field becomes mandatory for compliance."
    )
    pension_system_id = fields.Many2one(
        comodel_name='pension.system',
        string='Pension System',
        groups="hr.group_hr_user",
        help="The pension regime to which this employee is affiliated (e.g., SNP/ONP or a specific AFP). "
             "This determines which commission rates and monthly caps will be applied during payroll calculation. "
             "Required for all Peruvian employees to generate correct payroll deductions."
    )
    commission_type = fields.Selection(
        selection=[
            ('amount', 'Balance'),
            ('flow', 'Flow'),
        ],
        string='AFP Commission Type',
        groups="hr.group_hr_user",
        help="The AFP commission modality chosen by or assigned to this employee:\n"
             "• Balance: The commission is a percentage of the employee's managed fund balance (saldo).\n"
             "• Flow: The commission is a percentage of the employee's gross salary each month (flujo).\n"
             "Only applicable if the employee is enrolled in an AFP (not SNP/ONP)."
    )

    @api.depends('pension_system_id')
    def _compute_is_cuspp(self):
        for rec in self:
            if rec.pension_system_id and rec.pension_system_id.cuspp:
                rec.is_cuspp = True
            else:
                rec.is_cuspp = False
