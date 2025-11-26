# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_get_current_location(self):
        """
        Abre acción cliente para obtener coordenadas desde el dispositivo.
        """
        self.ensure_one()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'partner_current_location.get_location',
            'params': {
                'partner_id': self.id,
            }
        }

    @api.model
    def save_current_location(self, partner_id, latitude, longitude):
        """
        Guarda las coordenadas obtenidas desde JavaScript.
        """
        partner = self.browse(partner_id)
        if not partner.exists():
            raise UserError(_("Contacto no encontrado."))
        
        partner.write({
            'partner_latitude': latitude,
            'partner_longitude': longitude,
        })
        
        # Registrar en el chatter
        partner.message_post(
            body=_("Ubicación actualizada desde dispositivo: lat=%s, lon=%s") % (latitude, longitude)
        )
        
        return {
            'success': True,
            'latitude': latitude,
            'longitude': longitude,
        }