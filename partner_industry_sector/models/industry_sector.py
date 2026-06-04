from odoo import fields, models


class IndustrySector(models.Model):
    _name = "industry.sector"
    _description = "Industry Sector"
    _order = "name"

    name = fields.Char(
        string="Sector Name",
        required=True,
        translate=True,
        help="Unique sector name, shown when classifying contacts and when "
             "grouping or filtering them by sector.",
    )
    active = fields.Boolean(
        default=True,
        help="Uncheck to archive: kept on existing contacts but no longer "
             "selectable on new ones.",
    )

    _name_uniq = models.Constraint(
        "unique(name)",
        "The sector name must be unique.",
    )
