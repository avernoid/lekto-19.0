from odoo import api, fields, models
from lxml import etree
import json

class ProductUoM(models.Model):
    _inherit = 'uom.uom'

    l10n_pe_edi_measure_unit_code = fields.Char(
        string='Measure unit code',
        help="Unit code that relates to a product in order to identify what measure unit it uses, the possible values"
             " that you can use here can be found in this URL"
    )
    
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form' and self.env.ref('l10n_pe_edi.uom_uom_form_inherit_l10n_pe_edi'):
            for node in arch.xpath("//field[@name='l10n_pe_edi_measure_unit_code']"):
                modifiers = {'invisible': 1}
                node.set("modifiers", json.dumps(modifiers))
                break
        return arch, view
    