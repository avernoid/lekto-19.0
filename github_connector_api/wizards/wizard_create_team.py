from odoo import fields, models


class WizardCreateTeam(models.TransientModel):
    _name = "wizard.create.team"
    _description = "Wizard Create Team"
    _inherit = ["github.team"]

    # Overload Columns Section
    name = fields.Char(readonly=False)
    description = fields.Char(readonly=False)
    organization_id = fields.Many2one(readonly=False)
    privacy = fields.Selection(readonly=False)

    # Columns Section
    wizard_partner_ids = fields.Many2many(
        string="Team Members",
        comodel_name="res.partner",
        domain="[('github_name', '!=', False)]",
    )

    wizard_repository_ids = fields.Many2many(
        string="Team Repositories", 
        comodel_name="github.repository"
    )

    def get_github_data_from_odoo(self):
        self.ensure_one()
        res = super().get_github_data_from_odoo()
        res.update(
            {
                "maintainers": [
                    x.github_name for x in self.wizard_partner_ids if x.github_name
                ],
                "repo_names": [
                    x.github_name for x in self.wizard_repository_ids if x.github_name
                ],
            }
        )
        return res

    def button_create_in_github(self):
        # self.ensure_one()
        # self.delete_team()
        self.create_in_github(
            github_name = self.organization_id.github_name,
            team_name = self.name,
            team_description = self.description,
            team_privacy = self.privacy,
            team_members = self.wizard_partner_ids,
            team_repositories = self.wizard_repository_ids,
            
            )
        
        return self.env["ir.actions.act_window"]._for_xml_id("github_connector_api.action_github_team") 


    # def delete_team(self):
    #     gh_api = self.get_github_base_obj_for_creation()
    #  org_api = self.env['github.organization'].search(limit=1)
    #     gh_base_obj = gh_api.get_organization(org_api.github_name)
    #     team = gh_base_obj.get_team(id="Se coloca el id_external")
    #     team.delete()