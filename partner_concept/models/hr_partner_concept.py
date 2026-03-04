from odoo import fields, models


class HrPartnerConcept(models.Model):
    _name = 'hr.partner.concept'
    _description = 'Partner Concept'
    _rec_name = 'salary_rule_id'

    salary_rule_id = fields.Many2one(
        comodel_name='hr.salary.rule',
        string='Salary Rule',
        help='Select the specific salary rule this concept applies to. This links the custom amount directly to the chosen rule in the payslip computation.'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact',
        help='Employee or external contact linked to this salary concept. This determines who receives this specific rule.',
        ondelete='restrict'
    )
    amount = fields.Float(
        string='Amount',
        help='Fixed monetary amount to be applied by the salary rule for this specific employee.'
    )
    percentage = fields.Float(
        string='Percentage %',
        help='Percentage value to be computed by the salary rule. Useful for dynamic calculations based on the base salary.'
    )
    is_debit = fields.Boolean(
        string='Debit',
        help='Indicates if this concept acts as a debit (deduction) from the employee\'s net salary.'
    )
    is_credit = fields.Boolean(
        string='Credit',
        help='Indicates if this concept acts as a credit (allowance/bonus) added to the employee\'s net salary.'
    )
    is_active = fields.Boolean(
        string='Active',
        help='Uncheck this box to disable the concept without deleting it, preventing it from being applied in future payslips.'
    )
    start_date = fields.Date(
        string='Start Date',
        help='First day this concept is valid and will begin to be applied in payslips.'
    )
    end_date = fields.Date(
        string='End Date',
        help='Last day this concept is valid. Leave empty for ongoing rules that have no expiration.'
    )
