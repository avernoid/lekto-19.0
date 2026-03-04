from odoo import fields, models, api
from datetime import datetime
from dateutil.relativedelta import relativedelta


class HrVersion(models.Model):
    _inherit = 'hr.version'

    disability = fields.Boolean(
        string='Disability',
        help='Indicates whether the employee has a registered disability. '
             'When enabled, this flag can be used in payroll rules for special '
             'deductions or benefits applicable to employees with disabilities.',
        groups="hr.group_hr_user",
        tracking=True
    )

    advance_percent = fields.Float(
        string='Porcentaje de Anticipo',
        readonly=False,
    )

    def _get_whitelist_fields_from_template(cls):
        fields = super()._get_whitelist_fields_from_template()
        fields += [
            'disability',
            'advance_percent',
        ]
        return fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    disability = fields.Boolean(
        string='Disability',
        help='Inherited from the employee version. Indicates whether the '
             'employee has a registered disability status.',
        readonly=False,
        related='version_id.disability',
        inherited=True,
        groups="hr.group_hr_user"
    )

    advance_percent = fields.Float(
        string='Porcentaje de Anticipo',
        related='version_id.advance_percent',
        inherited=True,
        readonly=False,
    )

    age = fields.Float(
        string='Age',
        help='Age of the employee computed from their birthday.',
        compute='_compute_age',
        groups='hr.group_hr_user'
    )

    @api.depends('birthday')
    def _compute_age(self):
        for record in self:
            if record.birthday:
                delta = relativedelta(datetime.now(), record.birthday)
                record.age = delta.years + (delta.months / 12)
            else:
                record.age = 0.0
