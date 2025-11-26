from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campos de ubicación de la venta
    sale_latitude = fields.Float(
        string='Sale Latitude',
        digits=(10, 7),
        help='Latitude coordinate where the sale was registered'
    )
    
    sale_longitude = fields.Float(
        string='Sale Longitude',
        digits=(10, 7),
        help='Longitude coordinate where the sale was registered'
    )
    
    sale_location_date = fields.Datetime(
        string='Sale Location Date',
        readonly=True,
        help='Date and time when the sale location was captured'
    )

    # Campos computados para mostrar/ocultar botones según configuración del equipo
    show_update_partner_location = fields.Boolean(
        compute='_compute_location_settings',
        string='Show Update Partner Location'
    )
    
    show_register_sale_location = fields.Boolean(
        compute='_compute_location_settings',
        string='Show Register Sale Location'
    )
    
    capture_location_on_confirm = fields.Boolean(
        compute='_compute_location_settings',
        string='Capture Location on Confirm'
    )

    show_location_fields = fields.Boolean(
        compute='_compute_show_location_fields',
        string='Show Location Fields'
    )

    # Campos relacionados para mostrar ubicación del partner
    partner_latitude = fields.Float(
        related='partner_id.partner_latitude',
        string='Partner Latitude',
        readonly=True
    )
    
    partner_longitude = fields.Float(
        related='partner_id.partner_longitude',
        string='Partner Longitude',
        readonly=True
    )
    
    partner_date_localization = fields.Date(
        related='partner_id.date_localization',
        string='Partner Location Date',
        readonly=True
    )

    @api.depends('team_id', 'team_id.show_update_partner_location',
                 'team_id.show_register_sale_location',
                 'team_id.capture_location_on_confirm')
    def _compute_location_settings(self):
        """Obtiene la configuración del equipo de ventas"""
        for order in self:
            if order.team_id:
                order.show_update_partner_location = order.team_id.show_update_partner_location
                order.show_register_sale_location = order.team_id.show_register_sale_location
                order.capture_location_on_confirm = order.team_id.capture_location_on_confirm
            else:
                order.show_update_partner_location = False
                order.show_register_sale_location = False
                order.capture_location_on_confirm = False

    @api.depends('show_update_partner_location', 'show_register_sale_location', 
                 'capture_location_on_confirm')
    def _compute_show_location_fields(self):
        """Muestra los campos de ubicación solo si alguna opción está activa"""
        for order in self:
            order.show_location_fields = (
                order.show_update_partner_location or 
                order.show_register_sale_location or 
                order.capture_location_on_confirm
            )

    def action_update_partner_location(self):
        """
        Actualiza la ubicación del partner desde la ubicación actual del dispositivo.
        Retorna una acción para que JavaScript capture la ubicación.
        """
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('No partner assigned to this sale order.'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'update_partner_location_from_sale',
            'params': {
                'sale_order_id': self.id,
                'partner_id': self.partner_id.id,
            }
        }

    def action_register_sale_location(self):
        """
        Registra la ubicación de la venta desde la ubicación actual del dispositivo.
        Retorna una acción para que JavaScript capture la ubicación.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'register_sale_location',
            'params': {
                'sale_order_id': self.id,
            }
        }

    def action_view_sale_location_map(self):
        """Abre Google Maps con las coordenadas de la venta"""
        self.ensure_one()
        if not self.sale_latitude or not self.sale_longitude:
            raise UserError(_('No sale location coordinates available.'))
        
        maps_url = f"https://www.google.com/maps?q={self.sale_latitude},{self.sale_longitude}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': maps_url,
            'target': 'new',
        }

    def action_view_partner_location_map(self):
        """Abre Google Maps con las coordenadas del partner"""
        self.ensure_one()
        if not self.partner_id.partner_latitude or not self.partner_id.partner_longitude:
            raise UserError(_('No partner location coordinates available.'))
        
        maps_url = f"https://www.google.com/maps?q={self.partner_id.partner_latitude},{self.partner_id.partner_longitude}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': maps_url,
            'target': 'new',
        }

    def save_partner_location(self, latitude, longitude):
        """Guarda la ubicación en el partner asociado"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('No partner assigned to this sale order.'))
        
        self.partner_id.write({
            'partner_latitude': latitude,
            'partner_longitude': longitude,
            'date_localization': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Partner location updated successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def save_sale_location(self, latitude, longitude):
        """Guarda la ubicación de la venta"""
        self.ensure_one()
        self.write({
            'sale_latitude': latitude,
            'sale_longitude': longitude,
            'sale_location_date': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Sale location registered successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_confirm(self):
        """
        Override de action_confirm para capturar ubicación si está configurado
        y aún no hay ubicación guardada
        """
        # Verificar si necesitamos capturar ubicación antes de confirmar
        for order in self:
            if (order.capture_location_on_confirm and 
                not order.sale_latitude and 
                not order.sale_longitude):
                # Retornar acción para capturar ubicación antes de confirmar
                return {
                    'type': 'ir.actions.client',
                    'tag': 'capture_location_before_confirm',
                    'params': {
                        'sale_order_id': order.id,
                    }
                }
        
        # Si no necesita captura o ya tiene ubicación, confirmar normalmente
        return super(SaleOrder, self).action_confirm()

    def confirm_with_location(self, latitude, longitude):
        """Guarda ubicación y confirma la orden de venta"""
        self.ensure_one()
        
        # Guardar la ubicación
        self.write({
            'sale_latitude': latitude,
            'sale_longitude': longitude,
            'sale_location_date': fields.Datetime.now(),
        })
        
        # Confirmar la orden
        result = super(SaleOrder, self).action_confirm()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Sale order confirmed with location.'),
                'type': 'success',
                'sticky': False,
                'next': result if isinstance(result, dict) else None,
            }
        }

    def confirm_without_location(self):
        """Confirma la orden sin capturar ubicación"""
        self.ensure_one()
        return super(SaleOrder, self).action_confirm()