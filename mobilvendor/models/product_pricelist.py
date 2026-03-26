# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
from ..services.mobilvendor_api import MobilvendorAPIHandler

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def action_sync_mobilvendor(self):
        """
        Manually syncs selected price lists to Mobilvendor.
        As a safety measure, it first synchronizes the products contained in the pricelist
        to prevent missing dependency errors on the Mobilvendor side.
        """
        company = self.env.company
        if not company.mobilvendor_api_url:
            raise UserError(_("La compañía no tiene configurada la integración con Mobilvendor."))

        valid_pricelists = self.filtered(lambda p: p.active)
        if not valid_pricelists:
            raise UserError(_("Ninguna de las tarifas seleccionadas está activa."))

        # Extract all products involved in these pricelists
        # to ensure they exist in Mobilvendor before sending the price.
        pricelist_items = self.env['product.pricelist.item'].search([
            ('pricelist_id', 'in', valid_pricelists.ids)
        ])
        
        involved_products = pricelist_items.mapped('product_tmpl_id').filtered(
            lambda p: p.sale_ok and p.active and p.type == 'consu'
        )

        api_handler = MobilvendorAPIHandler(company=company, env=self.env)

        # 1. Dependency: Sync the products first
        if involved_products:
            api_handler._mobilvendor_articles(product_tmpl_ids=involved_products)
            api_handler._mobilvendor_article_units(product_tmpl_ids=involved_products)

        # 2. Sync the price list headers
        api_handler._mobilvendor_price_list(pricelist_ids=valid_pricelists)

        # 3. Sync the article prices for these specific pricelists
        api_handler._mobilvendor_article_prices(pricelist_ids=valid_pricelists)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Sincronización Exitosa"),
                'message': _("Se han enviado %s tarifas y %s productos pre-requisito." % (len(valid_pricelists), len(involved_products))),
                'type': 'success',
                'sticky': False,
            }
        }
