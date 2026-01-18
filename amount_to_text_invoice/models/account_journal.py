from odoo import models, fields, _

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    amount_text_format = fields.Selection(
        selection=[
            ('native', 'Odoo Native'),
            ('custom', 'Custom (00/100)'),
        ],
        string="Amount Text Format",
        default='custom',
        help="Choose the method to convert the invoice amount to text. 'Native' uses the standard Odoo format. 'Custom (00/100)' enforces strict legal formatting often required in Latin America."
    )

    amount_text_in_caps = fields.Boolean(
        string="Amount in Uppercase",
        default=False,
        help="Enable this to force the 'Amount in Words' to be displayed in specific UPPERCASE letters (e.g., 'ONE HUNDRED')."
    )

    amount_text_lang_id = fields.Many2one(
        'res.lang',
        string="Amount Text Language",
        domain="[('active', '=', True)]",
        help="Override the language used for the text amount. Useful if you need to issue invoices in a specific language (e.g., English) regardless of the customer's language setting. If empty, Odoo standard behavior (Customer Language) applies."
    )
