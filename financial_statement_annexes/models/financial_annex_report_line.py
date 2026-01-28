from odoo import models, fields

class FinancialAnnexReportLine(models.TransientModel):
    _name = 'financial.annex.report.line'
    _description = 'Financial Annex Report Line'

    wizard_id = fields.Many2one('wizard.report.financial', string='Wizard', ondelete='cascade')
    
    # Fields mirroring the Excel columns and keys in generate_data
    date = fields.Date(string='Date')
    account_name = fields.Char(string='Account') # Storing "Code Name" as single string to match Excel grouping key if needed, or just display
    partner_name = fields.Char(string='Partner')
    move_name = fields.Char(string='Journal Entry Name')
    ref = fields.Char(string='Reference')
    date_maturity = fields.Date(string='Due Date')
    expected_pay_date = fields.Date(string='Expected Date')
    name = fields.Char(string='Label')
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', readonly=True)
    balance = fields.Monetary(string='Residual Amount', currency_field='company_currency_id')
    amount_currency = fields.Float(string='Amount Currency', digits='Product Price')
    currency_id = fields.Many2one('res.currency', string='Currency')
    reconcile_name = fields.Char(string='Paid')
    date_reconcile = fields.Date(string='Payment Date')
    next_action_date = fields.Date(string='Next Action Date')
    internal_note = fields.Text(string='Internal Note')
    
    # Technical fields for grouping/linking
    account_id = fields.Many2one('account.account', string='Account Link')
    account_code = fields.Char(related='account_id.code', string='Info Account')
    partner_id = fields.Many2one('res.partner', string='Partner Link')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    move_line_id = fields.Many2one('account.move.line', string='Journal Item')

    # Aging buckets
    range_0_30 = fields.Monetary(string='1 - 30')
    range_31_60 = fields.Monetary(string='31 - 60')
    range_61_90 = fields.Monetary(string='61 - 90')
    range_91_120 = fields.Monetary(string='91 - 120')
    range_older = fields.Monetary(string='Older')
    range_not_due = fields.Monetary(string='Not Due') # Corresponds to "Por Vencer" if needed, or if logic separates it.
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
