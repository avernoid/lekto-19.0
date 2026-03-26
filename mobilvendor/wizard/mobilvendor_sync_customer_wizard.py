# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError
from ..services.mobilvendor_api import MobilvendorAPIHandler

class MobilvendorSyncCustomerWizard(models.TransientModel):
    _name = 'mobilvendor.sync.customer.wizard'
    _description = 'Mobilvendor: Descargar Cliente Específico'

    vat = fields.Char(string='Identificación (RUC/Cédula)', required=True, help="Ingrese la identificación exacta del cliente a buscar en Mobilvendor.")

    def action_sync_customer(self):
        """
        Llama a la API de Mobilvendor filtrando por la identificación proporcionada
        y fuerza la creación/actualización del cliente en Odoo.
        """
        company = self.env.company
        if not company.mobilvendor_api_url:
            raise UserError(_("La compañía no tiene configurada la integración con Mobilvendor."))

        api_handler = MobilvendorAPIHandler(company=company, env=self.env)
        
        # En el diseño actual, el filtro se inyecta en el JSON del request.
        # Se envía {'identification': XYZ} para que la API filtre. 
        # (El nombre exacto de la llave del filtro debe coincidir con la de Mobilvendor).
        filter_dict = {
            'identification': self.vat
        }
        
        # Ejecutamos la consulta pasándole el filtro específico
        api_handler._mobilvendor_get_customers(api_filter=filter_dict)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Búsqueda Solicitada"),
                'message': _("La consulta para el cliente con identificación %s ha sido procesada mediante la API de Mobilvendor.") % self.vat,
                'type': 'success',
                'sticky': False,
            }
        }
