from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    industry_sector_id = fields.Many2one(
        "industry.sector",
        string="Industry Sector",
        help="Sector this contact belongs to. On a child contact it is "
             "pre-filled from the parent company on creation, but can be "
             "changed independently afterwards. Lets you filter and group "
             "contacts by industry.",
    )

    @api.onchange("parent_id")
    def _onchange_parent_id_industry_sector(self):
        """Pre-fill the sector from the parent company when still empty (UI)."""
        for partner in self:
            if partner.parent_id and not partner.industry_sector_id:
                partner.industry_sector_id = partner.parent_id.industry_sector_id

    @api.model_create_multi
    def create(self, vals_list):
        """Pre-fill the sector from the parent company for records created
        without one (covers imports and programmatic creation, where the
        onchange does not run)."""
        for vals in vals_list:
            if vals.get("parent_id") and not vals.get("industry_sector_id"):
                parent = self.browse(vals["parent_id"])
                if parent.industry_sector_id:
                    vals["industry_sector_id"] = parent.industry_sector_id.id
        return super().create(vals_list)

    def action_inherit_industry_from_parent(self):
        """Mass action: overwrite the sector of the selected contacts with
        their parent company's sector. Records without a parent, or whose
        parent has no sector, are left untouched."""
        for partner in self:
            if partner.parent_id and partner.parent_id.industry_sector_id:
                partner.industry_sector_id = partner.parent_id.industry_sector_id
