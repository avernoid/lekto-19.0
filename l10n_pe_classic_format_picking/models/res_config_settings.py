from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_lot_on_delivery_slip = fields.Boolean(
        related='company_id.is_lot_on_delivery_slip',
        readonly=False
    )
    
    is_lot_expiry_date = fields.Boolean(
        related='company_id.is_lot_expiry_date',
        readonly=False
    )
    
    is_product_barcode = fields.Boolean(
        related='company_id.is_product_barcode',
        readonly=False
    )

    