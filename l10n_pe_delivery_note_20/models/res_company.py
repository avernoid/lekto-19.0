from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pe_edi_delivery_test_env = fields.Boolean(
        string="Entorno de prueba GRE"
    )
