from odoo import fields, models, api

class VariousDataSIS(models.Model):
    _name = 'various.data.sis'
    _description = 'Comprehensive Health Insurance (SIS)'

    register_date = fields.Date(
        string='Registration Date',
        help="Starting date from which this SIS contribution value becomes valid."
    )
    due_date = fields.Date(
        string='Expiration Date',
        help="End date until which this SIS contribution value remains valid."
    )
    sis_amount = fields.Float(
        string='Amount',
        help="The official contribution amount for the Comprehensive Health Insurance (SIS) applicable to microenterprises."
    )
    is_active = fields.Boolean(
        string='Active',
        help="If checked, this SIS value is currently active."
    )
    
    
    @api.depends('register_date','due_date')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.register_date} - {record.due_date}]"