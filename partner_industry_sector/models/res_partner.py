from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    industry_sector_id = fields.Many2one(
        "industry.sector",
        string="Industry Sector",
        help="Sector this customer belongs to. Lets you filter and group "
             "contacts by industry. Shown for customers only.",
    )
