from odoo import api, fields, models, _
import pytz
from odoo.exceptions import RedirectWarning, UserError, ValidationError

class Account(models.Model):
    _inherit = 'account.account'

    ple_date_account = fields.Date(
        string='Fecha de cuenta',
        default=fields.Date.today
    )
    ple_state_account = fields.Selection(
        selection=[
        ('1', '1'),
        ('8', '8'),
        ('9', '9')], 
        string='Estado', 
        default='1'
    )
    ple_selection = fields.Selection(
        selection=[],
        string='PLE'
    )