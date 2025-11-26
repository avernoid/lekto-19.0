from odoo import models, fields


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    # Configuración de geolocalización para el equipo de ventas
    show_update_partner_location = fields.Boolean(
        string='Show "Update Partner Location" Button',
        default=False,
        help='Show button to update partner coordinates from current device location'
    )
    
    show_register_sale_location = fields.Boolean(
        string='Show "Register Sale Location" Button',
        default=False,
        help='Show button to manually register sale location coordinates'
    )
    
    capture_location_on_confirm = fields.Boolean(
        string='Auto-capture Location on Sale Confirmation',
        default=False,
        help='Automatically capture device location when confirming a sale order'
    )