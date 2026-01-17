from odoo import api, fields, models, _


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    asset_brand = fields.Char(
        string="Brand",
        help="Brand of the asset (e.g. Dell, Toyota)"
    )
    asset_model = fields.Char(
        string="Item Model",
        help="Model of the asset (e.g. XPS 13, Corolla)"
    )
    asset_series = fields.Char(
        string="Series/Plate",
        help="Unique serial number or license plate of the asset"
    )



