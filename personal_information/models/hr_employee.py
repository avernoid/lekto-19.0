from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    firstname = fields.Char(
        string='First Name',
        groups='hr.group_hr_user',
        help='Employee first name.'
    )
    lastname = fields.Char(
        string='Paternal Lastname',
        groups='hr.group_hr_user',
        help='Employee paternal lastname.'
    )
    secondname = fields.Char(
        string='Maternal Lastname',
        groups='hr.group_hr_user',
        help='Employee maternal lastname.'
    )
    relative_ids = fields.One2many(
        string='Relatives',
        comodel_name='hr.employee.relative',
        inverse_name='employee_id',
        help='List of employee relatives.'
    )
    children = fields.Integer(
        compute='_compute_relatives_info',
        store=True,
        readonly=False,
        help='This field is updated from the "Relatives" tab.'
    )
    spouse_complete_name = fields.Char(
        compute='_compute_relatives_info',
        store=True,
        readonly=False,
        help='This field is updated from the "Relatives" tab.'
    )
    spouse_birthdate = fields.Date(
        compute='_compute_relatives_info',
        store=True,
        readonly=False,
        help='This field is updated from the "Relatives" tab.'
    )

    @api.onchange('firstname', 'lastname', 'secondname')
    def _onchange_capitalize_names(self):
        if self.firstname:
            self.firstname = self.firstname.title()
        if self.lastname:
            self.lastname = self.lastname.title()
        if self.secondname:
            self.secondname = self.secondname.title()

        parts = [self.firstname or '', self.lastname or '', self.secondname or '']
        full_name = ' '.join(p for p in parts if p).strip()

        if self.env.company.generate_employee_name:
            self.name = full_name

        if self.env.company.generate_legal_name:
            self.legal_name = full_name

    @api.depends('relative_ids', 'relative_ids.relation_id', 'relative_ids.name', 'relative_ids.date_of_birth')
    def _compute_relatives_info(self):
        spouse_relation = self.env.ref('personal_information.relation_spouse', raise_if_not_found=False)
        child_relation = self.env.ref('personal_information.relation_child', raise_if_not_found=False)
        for employee in self:
            children_count = 0
            spouse_name = False
            spouse_birthdate = False
            for relative in employee.relative_ids:
                if relative.relation_id == child_relation:
                    children_count += 1
                if relative.relation_id == spouse_relation:
                    spouse_name = relative.name
                    spouse_birthdate = relative.date_of_birth
            
            # Only update if we found something, or if the list was modified? 
            # Logic: If relatives are present, we take precedence. If not, we leave it?
            # User requirement: "que se autocompleten el registro de Parientes... pero igual dejarlos editables"
            # If I set it every time, manual edits are lost on any change to relatives. 
            # But that is the requested behavior: "se recalcularán"
            employee.children = children_count
            if spouse_name:
                employee.spouse_complete_name = spouse_name
            if spouse_birthdate:
                employee.spouse_birthdate = spouse_birthdate
