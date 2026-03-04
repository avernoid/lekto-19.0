from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LifeInsurance(models.Model):
    _name = 'life.insurance'
    _description = 'Life insurance'

    name = fields.Char(
        string='Policy Name',
        help='Name or reference of the life insurance policy.',
        required=True
    )        
    contacts_id = fields.Many2one(
        comodel_name='res.partner',
        string='Entities',
        help='Contact or entity providing the life insurance.',
    )
    nro = fields.Char(
        string='Policy Number',
        help='Unique number of the life insurance policy.'
    )
    start_date = fields.Date(
        string='Validity Start Date',
        help='Start date of the insurance policy validity.'
    )
    end_date = fields.Date(
        string='Validity End Date',
        help='End date of the insurance policy validity.'
    )
    hiring_term = fields.Char(
        string='Hiring Term',
        help='Term or duration of the life insurance hiring.'
    )
    rate = fields.Float(
        string='Rate',
        help='Rate applied to the life insurance policy.',
        digits=(16, 4),
    )
    amount = fields.Float(
        string='Amount',
        help='Amount covered by the life insurance.'
    )
    employees_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='Employees',
        help='List of employees covered by this life insurance policy.'
    )

    @api.constrains('employees_ids', 'start_date', 'end_date')
    def _check_employee_conflicts(self):
        for insurance in self:
            for employee in insurance.employees_ids:
                conflicting_insurances_up = self.env['life.insurance'].search([
                    ('id', '!=', insurance.id),
                    ('employees_ids', 'in', employee.id),
                    '|',
                    ('end_date', '>=', insurance.end_date), 
                    ('end_date', '>=', insurance.start_date)
                ])
                conflicting_insurances_down=self.env['life.insurance'].search([
                    ('id', '!=', insurance.id),
                    ('employees_ids', 'in', employee.id),
                    '|',
                    ('start_date', '<=', insurance.end_date), 
                    ('start_date', '<=', insurance.start_date)
                ])
                if conflicting_insurances_up and conflicting_insurances_down:
                    raise ValidationError(_("Employee %s has date conflicts with other insurances.") % employee.name)
    
    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            for employee in record.employees_ids:
                employee._onchange_life_insurance()
        return res    
    
    def write(self, values):
        result = super().write(values)
        if 'end_date' in values or 'employees_ids' in values:
            for record in self:
                for employee in record.employees_ids:
                    employee._onchange_life_insurance()
        return result
    
    def unlink(self):
        for record in self:
            for employee in record.employees_ids:
                most_recent_policy = self.env['life.insurance'].search([
                    ('employees_ids', 'in', employee.id),
                ], order='end_date desc', limit=2)
                if len(most_recent_policy) > 1 and most_recent_policy[0].id == record.id:
                    employee.life_insurance_id = most_recent_policy[1]
        return super().unlink()