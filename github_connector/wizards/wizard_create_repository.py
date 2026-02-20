from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


class WizardCreateRepository(models.TransientModel):
    _name = "wizard.create.repository"
    _description = "Wizard Create Repository"

    name = fields.Char(string="Name", required=True)
    website = fields.Char(string="Website", readonly=False)
    description = fields.Char(string="Description", readonly=False)
    organization_id = fields.Many2one(
        comodel_name="github.organization",
        string="Organization",
        required=True
    )
    template_repository_id = fields.Many2one(
        comodel_name="github.repository",
        string="Template Repository"
    )
    teams_ids = fields.Many2many(
        comodel_name="github.team",
        string="Assign to Teams"
    )

    def button_create_in_github(self):
        self.ensure_one()
        repository_obj = self.env['github.repository']
        if self.template_repository_id:
            repository_id = repository_obj.create_in_github_from_template(
                self.template_repository_id.github_name, self.name, self.organization_id, self.description)
        else:
            repository_id = repository_obj.create_in_github(self.name, self.organization_id, self.description, self.website)
        if self.teams_ids:
            gh_api = self.env['abstract.github.model'].get_github_connector()
            org = gh_api.get_organization(self.organization_id.github_name)
            gh_repo = gh_api.get_repo(repository_id.github_name)
            for team in self.teams_ids:
                gh_team = org.get_team(int(team.github_id_external))
                gh_team.add_to_repos(gh_repo)
                if gh_team.update_team_repository(gh_repo, 'push'):
                    _logger.info(f"GITHUB: Repository {repository_id.github_name} added to team {team.github_name} with push permission.")
                else:
                    _logger.warning(f"GITHUB: Error configuring push permission in repository {repository_id.github_name} - team {team.github_name}")
            prod_branch = gh_repo.default_branch
            test_branch = gh_repo.default_branch.split('.')[0] + '-dev'
            repository_id._create_new_branch(gh_repo, test_branch, prod_branch)
            repository_id.button_sync_branch()
            # team.button_sync_repository()

        action = self.env["ir.actions.act_window"]._for_xml_id("github_connector.action_github_repository")
        return action


    # def delete_repository(self):
    #     gh_base_obj = self.get_github_connector()
    #     repo = gh_base_obj.get_repo(int(idgithub))
    #     repo.delete()
        