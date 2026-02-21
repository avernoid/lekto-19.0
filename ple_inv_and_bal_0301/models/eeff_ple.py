from odoo import fields, models


class EEFFPLE(models.Model):
    _name = 'eeff.ple'
    _description = 'Rubro EEFF PLE'
    _inherit = 'model.sunat.catalog'
    _rec_names_search = ['code', 'description']

    sequence = fields.Integer(
        required=True,
        default=1,
        string='Secuencia'
    )
    # The 'parent_id' field had to be changed from Many2one to Many2many
    # This field will be hidden and for the next version remove this field
    parent_id = fields.Many2one(
        string='Padre (legacy)',
        comodel_name='eeff.ple'
    )
    parent_ids = fields.Many2many(
        'eeff.ple',
        'eeff_ple_eeff_ple_rel',
        'eeff_ple1_id',
        'eeff_ple2_id',
        string='Padre',
    )
    eeff_type = fields.Selection(
        selection=[
            ('3.1', '3.1 ESF'),
            ('3.18', '3.18 EFEMD'),
            ('3.19', '3.19 ECPN'),
            ('3.20', '3.20 EERR'),
            ('3.24', '3.24 ERI'),
            ('3.25', '3.25 EFEMI')
        ],
        string='Tipo'
    )
