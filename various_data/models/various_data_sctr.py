from odoo import api, fields, models
from odoo.exceptions import ValidationError

class VariousDataSCTR(models.Model):
    _name = 'various.data.sctr'
    _description = 'High Risk Work Complementary Insurance (SCTR)'

    register_date = fields.Date(
        string='Registration Date',
        help="Starting date from which this SCTR policy becomes valid."
    )
    due_date = fields.Date(
        string='Expiration Date',
        help="End date until which this SCTR policy remains valid. After this date, a new policy should be registered."
    )
    pension_percent = fields.Float(
        string='Pension %',
        help="Percentage of the contribution going towards the pension fund under this SCTR policy."
    )
    health_percent = fields.Float(
        string='Health %',
        help="Percentage of the contribution going towards the health fund under this SCTR policy."
    )
    pension_amount = fields.Float(
        string='Pension Amount',
        help="Fixed amount for the pension contribution, if applicable instead of a percentage."
    )
    health_amount = fields.Float(
        string='Health Amount',
        help="Fixed amount for the health contribution, if applicable instead of a percentage."
    )
    name_id = fields.Many2one(
        comodel_name='res.partner',
        string='Entity Name',
        help="The insurance company or entity providing this SCTR policy.",
        required=True
    )
    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        relation='hr_employee_sctr_rel',
        column1='sctr_id',
        column2='employee_id',
        string='Employees',
        help="List of employees currently covered by this specific SCTR policy."
    )
    
    sctr_name = fields.Char(
        string='Policy Name',
        help="Internal reference or official name for this SCTR policy."
    )

    @api.constrains('register_date', 'due_date')
    def _check_employee_overlap(self):
        for record in self:
            overlap_records = self.env['various.data.sctr'].search([
                ('id', '!=', record.id),
                ('name_id.employee_ids', 'in', record.name_id.employee_ids.ids),
                '|',
                ('register_date', '<=', record.register_date),
                ('register_date', '<=', record.due_date),
                '|',
                ('due_date', '>=', record.register_date),
                ('due_date', '>=', record.due_date),
            ])
            if overlap_records:
                raise ValidationError(
                    "Las fechas de esta póliza se superponen con otra póliza para uno o más empleados.")
                
                
    @api.depends('name_id')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name_id.name}"