# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError
from ..services.mobilvendor_api import MobilvendorAPIHandler

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_sync_mobilvendor(self):
        """
        Manually syncs selected product templates to Mobilvendor.
        Checks base requirements (sale_ok, active, consu) and triggers 
        the API handler for articles, units, and prices.
        """
        company = self.env.company
        if not company.mobilvendor_api_url:
            raise UserError(_("La compañía no tiene configurada la integración con Mobilvendor."))

        # Filter products that meet the Mobilvendor sync criteria
        valid_products = self.filtered(lambda p: p.sale_ok and p.active and p.type == 'consu')
        
        if not valid_products:
            raise UserError(_("Ninguno de los productos seleccionados cumple los criterios para ser sincronizado a Mobilvendor (Debe ser tipo Consumible, estar Activo y Disponible para la venta)."))
        
        # Initialize API handler
        api_handler = MobilvendorAPIHandler(company=company, env=self.env)
        
        # 1. Sync articles (master definition)
        api_handler._mobilvendor_articles(product_tmpl_ids=valid_products)
        # 2. Sync article units (barcodes/uoms)
        api_handler._mobilvendor_article_units(product_tmpl_ids=valid_products)
        # 3. Sync article prices (all associated prices for these products)
        api_handler._mobilvendor_article_prices(product_tmpl_ids=valid_products)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Sincronización Exitosa"),
                'message': _("Se han enviado %s productos a Mobilvendor exitosamente." % len(valid_products)),
                'type': 'success',
                'sticky': False,
            }
        }
