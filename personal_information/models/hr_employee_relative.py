from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrEmployeeRelative(models.Model):
    _name = 'hr.employee.relative'
    _description = 'HR Employee Relative'

    name = fields.Char(
        string='Name',
        required=True,
        help='Full name of the relative.'
    )
    job = fields.Char(
        string='Job',
        help='Job title or occupation of the relative.'
    )
    phone_number = fields.Char(
        string='Phone',
        help='Contact phone number.'
    )
    date_of_birth = fields.Date(
        string='Date of Birth',
        help='Birthdate of the relative.'
    )
    gender = fields.Selection(
        string='Gender',
        selection=[
            ('masculino', 'Male'),
            ('femenino', 'Female'),
            ('otro', 'Other')
        ],
        help='Gender of the relative.'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional information or comments.'
    )
    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        help='Age calculated based on Date of Birth.'
    )
    employee_id = fields.Many2one(
        string='Employee',
        comodel_name='hr.employee',
        help='Employee related to this person.'
    )
    relation_id = fields.Many2one(
        string='Relation',
        comodel_name='hr.employee.relative.relation',
        required=True,
        help='Type of relationship (e.g. Spouse, Child).'
    )
    partner_id = fields.Many2one(
        string='Contact',
        comodel_name='res.partner',
        domain="[('is_company', '=', False), ('type', '=', 'contact')]",
        help='Linked contact in the system.'
    )

    @api.constrains('date_of_birth')
    def _check_birthdate(self):
        for relative in self:
            if relative.date_of_birth and relative.date_of_birth > fields.Date.today():
                raise ValidationError('La fecha de nacimiento no puede ser futura.')

    @api.constrains('relation_id', 'employee_id')
    def _check_unique_spouse(self):
        spouse_relation = self.env.ref('personal_information.relation_spouse', raise_if_not_found=False)
        if not spouse_relation:
            return
        for relative in self:
            if relative.relation_id == spouse_relation and relative.employee_id:
                domain = [
                    ('employee_id', '=', relative.employee_id.id),
                    ('relation_id', '=', spouse_relation.id),
                    ('id', '!=', relative.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError('El empleado ya tiene un Cónyuge registrado.')

    @api.depends('date_of_birth')
    def _compute_age(self):
        for relative in self:
            age = 0
            if relative.date_of_birth:
                age = relativedelta(fields.Date.today(), relative.date_of_birth).years
            relative.age = age

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.name = self.partner_id.display_name
        else:
            self.name = False

    def action_open_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.relative',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
