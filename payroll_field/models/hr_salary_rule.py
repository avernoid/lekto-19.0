from odoo import models, fields

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    report_category_id = fields.Many2one(
        comodel_name='hr.salary.rule.report.category',
        string='Report Category',
        help='Category used to group different rules with the same behavior in pivot analysis reports.',
    )

    apply_advance_payroll = fields.Boolean(
        string='Applies Advance Payroll?',
        help='Check this if the salary rule must be applied during advance payroll processes.'
    )
