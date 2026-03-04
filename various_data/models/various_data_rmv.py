from odoo import fields, models,api

class VariousDataRMV(models.Model):
    _name = 'various.data.rmv'
    _description = 'Minimum Vital Remuneration'

    register_date = fields.Date(
        string='Registration Date',
        help="Starting date from which this RMV value becomes valid for payroll calculations."
    )
    due_date = fields.Date(
        string='Expiration Date',
        help="End date until which this RMV value remains valid. Leave empty if it is infinitely valid."
    )
    rmv_amount = fields.Float(
        string='RMV Amount',
        help="The official amount of the Minimum Vital Remuneration (RMV) established by the government for this period."
    )
    af_amount = fields.Float(
        string='Family Allowance Amount',
        help="The calculated or official amount corresponding to the Family Allowance (Asignación Familiar) for this period, generally 10% of RMV."
    )
    is_active = fields.Boolean(
        string='Active',
        help="If checked, this parameter is currently active and can be used in payroll rules."
    )
    
    @api.depends('register_date','due_date')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.register_date} - {record.due_date}]"