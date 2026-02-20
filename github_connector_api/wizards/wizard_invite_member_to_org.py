from odoo import fields, models


class WizardInviteMemberModel(models.TransientModel):
    _name = "wizard.invite.member.model"
    _description = "Wizard Invite Member Model"
    _inherit = "abstract.github.model"
    # Columns Section
    
    username = fields.Char(string="Username",
                           required=True)
    
    add_team_id = fields.Many2many(
        comodel_name="github.team",
        string="Team",
        required=True,
        index=True,
        ondelete="cascade",
    )


    def button_invite_member_from_odoo(self):
        list_team = []
        gh_api=self.env['abstract.github.model'].get_github_connector()
        org_api = self.env['github.organization'].search(limit=1)
        org = gh_api.get_organization(org_api.github_name)
        for item in self.add_team_id:
            list_team.append(org.get_team(int(item.github_id_external)))
        user=gh_api.get_user(self.username)
        org.invite_user(user=user,
                        teams  = list_team,)
        
