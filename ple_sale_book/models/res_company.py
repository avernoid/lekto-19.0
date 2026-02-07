from odoo import api, fields, models
from lxml import etree
import json

class ResCompany(models.Model):
    _inherit = 'res.company'

    ple_type_contributor = fields.Selection(
        selection=[
        ('CUO', 'Contribuyentes del Régimen General'),
        ('RER', 'Contribuyentes del Régimen Especial de Renta')], 
        string='Tipo de contribuyente'
    )