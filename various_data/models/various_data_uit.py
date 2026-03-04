from odoo import fields, models, api

class VariousDataUIT(models.Model):
    _name = 'various.data.uit'
    _description = 'Tax Unit'

    register_date = fields.Date(
        string='Registration Date',
        help="Starting date from which this UIT value becomes valid."
    )
    due_date = fields.Date(
        string='Expiration Date',
        help="End date until which this UIT value remains valid, usually the end of the fiscal year."
    )
    uit_amount = fields.Float(
        string='Amount',
        help="The official amount of the Unidad Impositiva Tributaria (UIT) for this period, used in 5th category income tax calculations."
    )
    is_active = fields.Boolean(
        string='Active',
        help="If checked, this UIT value is currently active."
    )
    
    @api.depends('register_date','due_date')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.register_date} - {record.due_date}]"