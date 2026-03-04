# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    # Academic & Personal Information
    academic_degree_id = fields.Many2one(
        comodel_name='academic.degree',
        string='Academic Degree',
        help='Educational level of the employee according to SUNAT classification. '
             'Used in official payroll reports (T-Registro, PLAME).',
        groups="hr.group_hr_user",
        tracking=True
    )

    health_regime_id = fields.Many2one(
        comodel_name='health.regime',
        string='Health Regime',
        help='Health coverage type assigned to the employee (e.g., EsSalud, EPS). '
             'Determines health contribution calculations in payroll.',
        groups="hr.group_hr_user",
        tracking=True
    )


    # Labor Information
    labor_regime_id = fields.Many2one(
        comodel_name='employee.regime',
        string='Labor Regime',
        help='Employment regime under which the employee works (e.g., General Private Regime, '
             'MYPE, Public Sector). Required for SUNAT T-Registro declarations.',
        groups="hr.group_hr_user",
        tracking=True
    )
    labor_condition_id = fields.Many2one(
        comodel_name='type.contract',
        string='Labor Condition',
        help='Type of employment contract (e.g., Indefinite, Fixed-term, Part-time). '
             'Used in payroll calculations and SUNAT reporting.',
        groups="hr.group_hr_user",
        tracking=True
    )
    maximum_working_day = fields.Boolean(
        string='Maximum Working Day',
        help='Enable if the employee works the maximum legal working hours (48 hours/week in Peru). '
             'Affects overtime calculation rules.',
        groups="hr.group_hr_user",
        tracking=True
    )
    atypical_cumulative_day = fields.Boolean(
        string='Atypical Cumulative Day',
        help='Enable if the employee has an atypical or cumulative work schedule '
             '(e.g., mining shifts, 14x7 rotations). Affects rest day calculations.',
        groups="hr.group_hr_user",
        tracking=True
    )
    nocturnal_schedule = fields.Boolean(
        string='Nocturnal Schedule',
        help='Enable if the employee works night shifts (between 10:00 PM and 6:00 AM). '
             'Triggers the 35% nocturnal surcharge in payroll calculations.',
        groups="hr.group_hr_user",
        tracking=True
    )
    unionized = fields.Boolean(
        string='Unionized',
        help='Enable if the employee is a member of a labor union. '
             'May affect specific payroll deductions and benefits.',
        groups="hr.group_hr_user",
        tracking=True
    )
    is_practitioner = fields.Boolean(
        string='Is Practitioner',
        help='Enable if the employee is an intern or trainee (practicante). '
             'Practitioners have different contribution rules and minimum wage thresholds.',
        groups="hr.group_hr_user",
        tracking=True
    )
    work_occupation_id = fields.Many2one(
        comodel_name='work.occupation',
        string='Work Occupation',
        help='Job category classification (Executive, Employee, Worker). '
             'Used for SUNAT reporting and CTS calculation rules.',
        groups="hr.group_hr_user",
        tracking=True
    )


    @api.model
    def _get_whitelist_fields_from_template(self):
        # Add new fields to the whitelist
        whitelist = super()._get_whitelist_fields_from_template()
        new_fields = [
            'labor_regime_id',
            'labor_condition_id',
            'maximum_working_day',
            'atypical_cumulative_day',
            'nocturnal_schedule',
            'unionized',
            'is_practitioner',
            'work_occupation_id'
        ]
        return whitelist + new_fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Academic & Personal Information
    academic_degree_id = fields.Many2one(
        comodel_name='academic.degree',
        string='Academic Degree',
        help='Educational level of the employee according to SUNAT classification. '
             'Used in official payroll reports (T-Registro, PLAME).',
        readonly=False,
        related='version_id.academic_degree_id',
        inherited=True,
        groups="hr.group_hr_user"
    )

    health_regime_id = fields.Many2one(
        comodel_name='health.regime',
        string='Health Regime',
        help='Health coverage type assigned to the employee (e.g., EsSalud, EPS). '
             'Determines health contribution calculations in payroll.',
        readonly=False,
        related='version_id.health_regime_id',
        inherited=True,
        groups="hr.group_hr_user"
    )


    # Labor Information
    labor_regime_id = fields.Many2one(
        comodel_name='employee.regime',
        string='Labor Regime',
        help='Employment regime under which the employee works (e.g., General Private Regime, '
             'MYPE, Public Sector). Required for SUNAT T-Registro declarations.',
        readonly=False,
        related='version_id.labor_regime_id',
        inherited=True,
        groups="hr.group_hr_user"
    )
    labor_condition_id = fields.Many2one(
        comodel_name='type.contract',
        string='Labor Condition',
        help='Type of employment contract (e.g., Indefinite, Fixed-term, Part-time). '
             'Used in payroll calculations and SUNAT reporting.',
        readonly=False,
        related='version_id.labor_condition_id',
        inherited=True,
        groups="hr.group_hr_user"
    )
    maximum_working_day = fields.Boolean(
        string='Maximum Working Day',
        help='Enable if the employee works the maximum legal working hours (48 hours/week in Peru). '
             'Affects overtime calculation rules.',
        readonly=False,
        related='version_id.maximum_working_day',
        inherited=True,
        groups="hr.group_hr_user"
    )
    atypical_cumulative_day = fields.Boolean(
        string='Atypical Cumulative Day',
        help='Enable if the employee has an atypical or cumulative work schedule '
             '(e.g., mining shifts, 14x7 rotations). Affects rest day calculations.',
        readonly=False,
        related='version_id.atypical_cumulative_day',
        inherited=True,
        groups="hr.group_hr_user"
    )
    nocturnal_schedule = fields.Boolean(
        string='Nocturnal Schedule',
        help='Enable if the employee works night shifts (between 10:00 PM and 6:00 AM). '
             'Triggers the 35% nocturnal surcharge in payroll calculations.',
        readonly=False,
        related='version_id.nocturnal_schedule',
        inherited=True,
        groups="hr.group_hr_user"
    )
    unionized = fields.Boolean(
        string='Unionized',
        help='Enable if the employee is a member of a labor union. '
             'May affect specific payroll deductions and benefits.',
        readonly=False,
        related='version_id.unionized',
        inherited=True,
        groups="hr.group_hr_user"
    )
    is_practitioner = fields.Boolean(
        string='Is Practitioner',
        help='Enable if the employee is an intern or trainee (practicante). '
             'Practitioners have different contribution rules and minimum wage thresholds.',
        readonly=False,
        related='version_id.is_practitioner',
        inherited=True,
        groups="hr.group_hr_user"
    )
    work_occupation_id = fields.Many2one(
        comodel_name='work.occupation',
        string='Work Occupation',
        help='Job category classification (Executive, Employee, Worker). '
             'Used for SUNAT reporting and CTS calculation rules.',
        readonly=False,
        related='version_id.work_occupation_id',
        inherited=True,
        groups="hr.group_hr_user"
    )