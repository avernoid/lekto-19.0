from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    is_lot_on_delivery_slip = fields.Boolean(
        string='Mostrar números de lote y serie en Guías de Remisión',
        default=False
    )
    
    is_lot_expiry_date = fields.Boolean(
        string='Mostrar la fecha de caducidad en Guías de Remisión',
        default=False
    )
    
    is_product_barcode = fields.Boolean(
        string='Mostrar Ean del producto en Guía de Remisión',
        default=False
    )