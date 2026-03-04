from odoo import models, fields

class HrSalaryRuleReportCategory(models.Model):
    _name = 'hr.salary.rule.report.category'
    _description = 'Report Categories for Salary Rules'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
    )
    code = fields.Char(
        string='Code',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence determines the order of the columns in pivot views.',
    )
    appears_on_payslip = fields.Boolean(
        string='Appears on Payslip Analysis',
        default=True,
        help='If checked, rules under this category will appear in the specific filtered views by default.',
    )
    parent_id = fields.Many2one(
        comodel_name='hr.salary.rule.report.category',
        string='Parent Category',
        index=True,
    )
