
from odoo import fields, models


class GithubOrganizationSerie(models.Model):
    _name = "github.organization.serie"
    _description = "Github Organization Serie"
    _order = "sequence, name"

    # Columns Section
    name = fields.Char(required=True)

    sequence = fields.Integer(required=True)

    organization_id = fields.Many2one(
        comodel_name="github.organization",
        string="Organization",
        ondelete="cascade",
        required=True,
    )

    _sql_constraints = [
        (
            "sequence_organization_uniq",
            "unique(organization_id, sequence)",
            "Sequence serie must be unique by organization.",
        )
    ]
