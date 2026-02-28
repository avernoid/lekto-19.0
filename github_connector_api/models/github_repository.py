from odoo import api, fields, models
from odoo.exceptions import UserError
import logging
import requests

_logger = logging.getLogger(__name__)


class GithubRepository(models.Model):
    _name = "github.repository"
    _inherit = ["abstract.github.model"]
    _order = "organization_id, name"
    _description = "Github Repository"

    _github_login_field = "full_name"

    # Column Section
    organization_id = fields.Many2one(
        comodel_name="github.organization",
        string="Organization",
        required=True,
        index=True,
        readonly=True,
        ondelete="cascade",
        help="The GitHub Organization that owns this repository.",
    )

    name = fields.Char(
        index=True, 
        required=True, 
        readonly=True,
        help="The name of the repository.",
    )

    complete_name = fields.Char(
        readonly=True,
        compute="_compute_complete_name",
        store=True,
        help="Full name of the repository (Organization/Name).",
    )

    description = fields.Char(
        readonly=True,
        help="Description of the repository fetched from GitHub.",
    )

    website = fields.Char(
        readonly=True,
        help="Website URL linked to the repository.",
    )

    repository_branch_ids = fields.One2many(
        comodel_name="github.repository.branch",
        inverse_name="repository_id",
        string="Branches",
        readonly=True,
        help="List of branches synchronized for this repository.",
    )

    repository_branch_qty = fields.Integer(
        string="Number of Branches",
        compute="_compute_repository_branch_qty",
        store=True,
        help="Total count of branches in this repository.",
    )

    team_ids = fields.One2many(
        string="Teams",
        comodel_name="github.team.repository",
        inverse_name="repository_id",
        readonly=True,
        help="List of teams that have access to this repository.",
    )

    team_qty = fields.Integer(
        string="Number of Teams", 
        compute="_compute_team_qty", 
        store=True,
        help="Total count of teams associated with this repository.",
    )

    is_ignored = fields.Boolean(
        compute="_compute_ignore",
        help="If checked, this repository is ignored based on the Organization's 'Ignored Repositories' list."
        " Ignored repositories are not synchronized (no branch sync, no source code download).",
    )

    color = fields.Integer(
        string="Color Index", 
        compute="_compute_ignore"
    )

    inhibit_inherited_rules = fields.Boolean(
        string="Inhibit Inherited Rules",
        default=False,
        help="If checked, the analysis rules from the Organization will NOT be applied to this repository."
        " Only the rules defined specifically on this repository will be used.",
    )

    analysis_rule_ids = fields.Many2many(
        string="Analysis Rules", 
        comodel_name="github.analysis.rule",
        help="Specific analysis rules applied to this repository.",
    )

    is_github_repository_template = fields.Boolean(
        string='Is Template Repository',
        help="Indicates if this repository is a template repository on GitHub.",
    )

    # Compute Section
    @api.depends("organization_id.ignored_repository_names")
    def _compute_ignore(self):
        for repository in self:
            ignored_txt = repository.organization_id.ignored_repository_names
            repository.is_ignored = (
                ignored_txt and repository.name in ignored_txt.split("\n")
            )
            repository.color = repository.is_ignored and 1 or 0

    @api.depends("team_ids")
    def _compute_team_qty(self):
        data = self.env["github.team.repository"].read_group(
            [("repository_id", "in", self.ids)], ["repository_id"], ["repository_id"]
        )
        mapping = {
            data["repository_id"][0]: data["repository_id_count"] for data in data
        }
        for item in self:
            item.team_qty = mapping.get(item.id, 0)

    @api.depends("name", "organization_id.github_name")
    def _compute_complete_name(self):
        for repository in self:
            repository.complete_name = "%(login)s/%(rep_name)s" % (
                {
                    "login": repository.organization_id.github_name,
                    "rep_name": repository.name or "",
                }
            )

    @api.depends("repository_branch_ids.repository_id")
    def _compute_repository_branch_qty(self):
        data = self.env["github.repository.branch"].read_group(
            [("repository_id", "in", self.ids)], ["repository_id"], ["repository_id"]
        )
        mapping = {
            data["repository_id"][0]: data["repository_id_count"] for data in data
        }
        for item in self:
            item.repository_branch_qty = mapping.get(item.id, 0)

    # Overloadable Section
    @api.model
    def get_conversion_dict(self):
        res = super().get_conversion_dict()
        res.update(
            {
                "name": "name",
                "description": "description",
                "website": "homepage",
                "is_github_repository_template": "is_template"
            }
        )
        return res

    @api.model
    def get_odoo_data_from_github(self, gh_data):
        res = super().get_odoo_data_from_github(gh_data)
        org_id = self.env.context.get("github_organization_id", None)
        if not org_id:
            # Fetch current organization object
            organization_obj = self.env["github.organization"]
            organization = organization_obj.get_from_id_or_create(gh_data=gh_data.owner)
            org_id = organization.id
        res.update({"organization_id": org_id})
        return res

    def find_related_github_object(self, obj_id=None):
        """Query Github API to find the related object"""
        gh_api = self.get_github_connector()
        return gh_api.get_repo(int(obj_id or self.github_id_external))

    def get_github_base_obj_for_creation(self):
        self.ensure_one()
        gh_api = self.get_github_connector()
        return gh_api.get_organization(self.organization_id.github_name)

    def _get_analysis_rules(self):
        if self.inhibit_inherited_rules:
            return self.analysis_rule_ids
        return self.organization_id.analysis_rule_ids + self.analysis_rule_ids

    @staticmethod
    def _create_new_branch(repository_obj, branch_name, source_branch):
        _logger.info('GITHUB: Creating new branch %s from %s in repository %s', branch_name, source_branch, repository_obj.full_name)
        branch_obj = repository_obj.get_branch(source_branch)
        try:
            repository_obj.create_git_ref(ref=f'refs/heads/{branch_name}', sha=branch_obj.commit.sha)
        except Exception as e:
            raise UserError(f"La rama {branch_name} ya ha sido creado o los valores ingresados son correctos, se adjunta el posible error: {e}")

    def create_in_github(self, name, organization_id, description=None, website=None):
        """Create an object in Github through the github library"""
        gh_base_obj = self.get_github_base_obj_for_creation()
        gh_repo = gh_base_obj.create_repo(
            name=name,
            description=description or "" ,
            auto_init=True,
            private=True,
            homepage=website or ""
        )

        new_item = self.synch_repository_from_github(organization_id, gh_repo)
        return new_item

    def create_in_github_from_template(self, template_full_name, name, organization_id, description, include_all_branches=False):
        """Create an object in Github through the API (using a template)"""
        github_access_token = self.get_github_token()

        if not github_access_token:
            raise UserError("No se encontró token de GitHub (conector o GITHUB_TOKEN).")

        template_owner, template_repo = template_full_name.split("/", 1)
        url = f"https://api.github.com/repos/{template_owner}/{template_repo}/generate"
        headers = {
            "Authorization": f"token {github_access_token}",
            "Accept": "application/vnd.github.baptiste-preview+json",
        }
        payload = {
            "name": name.replace(" ", ""),
            "owner": organization_id.github_name,
            "description": description or "",
            "private": True,
            "include_all_branches": bool(include_all_branches),
        }

        try:
            resp = requests.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # intentar extraer mensaje detallado del JSON de la respuesta
            details = None
            try:
                err_json = resp.json()
                msg = err_json.get("message") or ""
                errs = err_json.get("errors") or ""
                details = f"{msg} - {errs}" if errs else msg
            except Exception:
                details = getattr(resp, "text", str(e))
            raise UserError(f"Error al crear repositorio desde plantilla: {details}")
        except requests.exceptions.RequestException as e:
            raise UserError(f"Error de conexión al crear repositorio desde plantilla: {e}")

        gh_repo = resp.json()
        new_item = self.synch_repository_from_github(organization_id, gh_repo)
        return new_item

    def synch_repository_from_github(self, organization_id, gh_repo):
        # Create in Odoo with the returned data and update object
        data = self.with_context(github_organization_id=organization_id.id).get_odoo_data_from_github(gh_repo)
        new_item = self._create_from_github_data(data)
        new_item.full_update()
        new_item._hook_after_github_creation()
        return new_item

    def full_update(self):
        self.button_sync_branch()

    # def button_synch_repository(self):
    #     gh_repo = self.find_related_github_object()
    #     get_from_id_or_create(gh_data=gh_repo)
    #     print("gh_org")
    #     print(gh_org)

    # def add_branch_in_new_repo(self,gh_repo):
    #     correct_series = self.organization_id.organization_serie_ids.mapped("name")
    #     for branch in correct_series:
    #         print("branch.name:",branch)
    #         gh_repo.create_git_ref(ref=f'refs/heads/{branch}', sha=gh_repo.get_commit("main").sha)
    #     self.full_update()
    #     print("salio del for")
    #     print("newx3")


    @api.model
    def cron_update_branch_list(self):
        branches = self.search([])
        branches.button_sync_branch()
        return True

    def button_sync_branch(self):
        branch_obj = self.env["github.repository.branch"]
        for repository in self.filtered(lambda r: not r.is_ignored):
            gh_repo = repository.find_related_github_object()
            branch_ids = []
            correct_series = repository.organization_id.organization_serie_ids.mapped(
                "name"
            )
            
            for gh_branch in gh_repo.get_branches():
                
                if gh_branch.name in correct_series:
                    # We don't use get_from_id_or_create because repository
                    # branches does not have any ids. (very basic object in the
                    # Github API)
                    
                    branch = branch_obj.create_or_update_from_name(
                        repository.id, gh_branch.name
                    )
                    branch_ids.append(branch.id)
                    
                else:
                    
                    _logger.warning(
                        "the branch '%s'/'%s' has been ignored.",
                        repository.name,
                        gh_branch.name,
                    )

            repository.repository_branch_ids = [(6, 0, branch_ids)]

    def action_github_team_repository_from_repository(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "github_connector_api.action_github_team_repository_from_repository"
        )
        action["context"] = dict(self.env.context)
        action["context"].pop("group_by", None)
        action["context"]["search_default_repository_id"] = self.id
        return action

    def action_github_repository_branch(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "github_connector_api.action_github_repository_branch"
        )
        action["context"] = dict(self.env.context)
        action["context"].pop("group_by", None)
        action["context"]["search_default_repository_id"] = self.id
        return action
