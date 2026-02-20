from odoo import fields, models, api


class WizardAddMemberTeam(models.TransientModel):
    _name = "wizard.member.repo.team"
    _description = "Wizard Add Member to Team"

    add_oldteam_id = fields.Many2one(
        comodel_name="github.team",
        string="Selecciona Equipo",
        required=True,
        index=True,
        ondelete="cascade",
    )
    wizard_not_partner_ids = fields.Many2many(
        string="Miembros del equipo",
        comodel_name="res.partner",
        compute="get_data_partner_from_github",
    )
    wizard_partner_ids = fields.Many2many(
        string="Agregar miembros al equipo",
        comodel_name="res.partner",
        domain="[('id', 'not in', wizard_not_partner_ids),('github_name', '!=',False)]",
    )
    wizard_not_repository_ids = fields.Many2many(
        string="Repositorios Asignados",
        comodel_name="github.repository",
        compute="get_data_partner_from_github",
    )
    wizard_repository_ids = fields.Many2many(
        string="Agregar nuevo repositorio",
        comodel_name="github.repository",
        domain="[('github_name', '!=', False),('id', 'not in', wizard_not_repository_ids)]",
    )

    @api.depends('add_oldteam_id')
    def get_data_partner_from_github(self):
        self.write({
            'wizard_not_partner_ids': [(6, 0, self.add_oldteam_id.partner_ids.partner_id.ids)],
            'wizard_not_repository_ids': [(6, 0, self.add_oldteam_id.repository_ids.repository_id.ids)],
        })

    def button_add_member_repo_to_team(self):
        gh_api = self.env['abstract.github.model'].get_github_connector()
        org_api = self.env['github.organization'].search([('id', '!=', False)], limit=1)
        org = gh_api.get_organization(org_api.github_name)
        gh_team = org.get_team(int(self.add_oldteam_id.github_id_external))
        if self.wizard_partner_ids and len(self.wizard_partner_ids) > 0:
            list(map(lambda member: gh_team.add_membership(gh_api.get_user(member.github_name), role="member"), self.wizard_partner_ids))
            self.add_oldteam_id.button_sync_member()

        if self.wizard_repository_ids and len(self.wizard_repository_ids) > 0:
            list(map(lambda repo: gh_team.add_to_repos(gh_api.get_repo(repo.github_name)), self.wizard_repository_ids))
            self.add_oldteam_id.button_sync_repository()
