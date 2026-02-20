
from datetime import datetime, timedelta
import logging
from github.GithubException import GithubException

_logger = logging.getLogger(__name__)

from odoo import _, api, exceptions, fields, models


class GithubOrganization(models.Model):
    _name = "github.organization"
    _inherit = ["abstract.github.model"]
    _order = "name"
    _description = "Github organization"

    _github_login_field = "login"

    # Columns Section
    name = fields.Char(
        string="Organization Name", 
        required=True, 
        readonly=True,
        help="The name of the GitHub Organization (e.g., 'ganemo').",
    )

    image = fields.Image(
        readonly=True,
        help="Avatar of the Organization fetched from GitHub.",
    )

    description = fields.Char(
        readonly=True,
        help="Description of the Organization fetched from GitHub.",
    )

    email = fields.Char(
        readonly=True,
        help="Public email of the Organization.",
    )

    website_url = fields.Char(
        readonly=True,
        help="Website URL of the Organization.",
    )

    location = fields.Char(
        readonly=True,
        help="Location of the Organization.",
    )

    ignored_repository_names = fields.Text(
        string="Ignored Repositories",
        help="Set here repository names (one per line) that you want to ignore during synchronization."
        " These repositories will be created in Odoo but will NOT sync branches or download source code."
        " Useful for archiving or ignoring forks.\n"
        " Example:\n"
        " purchase-workflow\n"
        " OCB\n",
    )

    member_ids = fields.Many2many(
        string="Members",
        comodel_name="res.partner",
        relation="github_organization_partner_rel",
        column1="organization_id",
        column2="partner_id",
        readonly=True,
        help="List of members belonging to this Organization in GitHub, mapped to Odoo Partners.",
    )

    member_qty = fields.Integer(
        string="Number of Members", 
        compute="_compute_member_qty", 
        store=True,
        help="Total count of members in this Organization.",
    )

    repository_ids = fields.One2many(
        string="Repositories",
        comodel_name="github.repository",
        inverse_name="organization_id",
        readonly=True,
        help="List of repositories owned by this Organization.",
    )

    repository_qty = fields.Integer(
        string="Number of Repositories", 
        compute="_compute_repository_qty", 
        store=True,
        help="Total count of repositories in this Organization.",
    )

    team_ids = fields.One2many(
        string="Teams",
        comodel_name="github.team",
        inverse_name="organization_id",
        readonly=True,
        help="List of teams defined in this Organization.",
    )

    team_qty = fields.Integer(
        string="Number of Teams", 
        compute="_compute_team_qty", 
        store=True,
        help="Total count of teams in this Organization.",
    )

    organization_serie_ids = fields.One2many(
        string="Organization Series",
        comodel_name="github.organization.serie",
        inverse_name="organization_id",
        help="Define here the series (e.g., '16.0', '17.0') to filter which branches are synchronized."
             " Only branches matching these series will be synced.",
    )

    organization_serie_qty = fields.Integer(
        string="Number of Series", 
        store=True, 
        compute="_compute_organization_serie_qty",
        help="Total count of configured series.",
    )

    coverage_url_pattern = fields.Char(
        string="Coverage URL Pattern",
        help="URL pattern for code coverage reports (e.g., https://coverage.example.com/{branch}).",
    )

    ci_url_pattern = fields.Char(
        string="CI URL Pattern",
        help="URL pattern for Continuous Integration status (e.g., https://ci.example.com/{branch}).",
    )

    analysis_rule_ids = fields.Many2many(
        string="Analysis Rules", 
        comodel_name="github.analysis.rule",
        help="Rules for code analysis applied to this Organization.",
    )

    repository_sync_limit = fields.Integer(
        string="Branch Sync Limit per Batch",
        default=20,
        help="Maximum number of repositories to synchronize branches for in a single execution."
             " Use this to prevent Timeouts on large organizations.",
    )

    last_search_cursor = fields.Datetime(
        string="Last Search Cursor",
        help="Timestamp of the last processed repository. Used for incremental sync with Search API.",
        readonly=False, # Editable for debugging/reset
    )

    sync_filter_topics = fields.Char(
        string="Sync Filter Topics",
        help="GitHub topics to filter which repositories are synchronized.\n\n"
             "• Empty: Syncs ALL repositories (no topic filter).\n"
             "• One topic: Only repos with that topic are synced.\n"
             "  Example: odoo-sync\n"
             "• Multiple topics (comma-separated): The FIRST topic is required (AND). "
             "From the remaining topics, the repo must have at least one (OR).\n"
             "  Example: odoo-sync, odoo-module, priority\n"
             "  Result: repos with 'odoo-sync' AND ('odoo-module' OR 'priority')\n\n"
             "Topics must match the ones configured in your GitHub repositories "
             "(Settings > Topics).",
    )

    # Overloadable Section
    @api.model
    def get_conversion_dict(self):
        res = super().get_conversion_dict()
        res.update(
            {
                "name": "name",
                "description": "description",
                "location": "location",
                "email": "email",
                "website_url": "blog",
            }
        )
        return res

    @api.model
    def get_odoo_data_from_github(self, gh_data):
        res = super().get_odoo_data_from_github(gh_data)
        if hasattr(gh_data, "avatar_url"):
            res.update({"image": self.get_base64_image_from_github(gh_data.avatar_url)})
        return res

    def full_update(self):
        self.button_sync_member()
        self.button_sync_repository()
        self.button_sync_team()

    @api.model
    def cron_update_organization_team(self):
        organizations = self.search([])
        organizations.full_update()
        organizations.mapped("team_ids").full_update()
        return True

    # Compute Section
    @api.depends("member_ids", "member_ids.organization_ids")
    def _compute_member_qty(self):
        for organization in self:
            organization.member_qty = len(organization.member_ids)

    @api.depends("repository_ids.organization_id")
    def _compute_repository_qty(self):
        data = self.env["github.repository"].read_group(
            [("organization_id", "in", self.ids)],
            ["organization_id"],
            ["organization_id"],
        )
        mapping = {
            data["organization_id"][0]: data["organization_id_count"] for data in data
        }
        for item in self:
            item.repository_qty = mapping.get(item.id, 0)

    @api.depends("team_ids.organization_id")
    def _compute_team_qty(self):
        data = self.env["github.team"].read_group(
            [("organization_id", "in", self.ids)],
            ["organization_id"],
            ["organization_id"],
        )
        mapping = {
            data["organization_id"][0]: data["organization_id_count"] for data in data
        }
        for item in self:
            item.team_qty = mapping.get(item.id, 0)

    @api.depends("organization_serie_ids.organization_id")
    def _compute_organization_serie_qty(self):
        data = self.env["github.organization.serie"].read_group(
            [("organization_id", "in", self.ids)],
            ["organization_id"],
            ["organization_id"],
        )
        mapping = {
            data["organization_id"][0]: data["organization_id_count"] for data in data
        }
        for item in self:
            item.organization_serie_qty = mapping.get(item.id, 0)

    def find_related_github_object(self, obj_id=None):
        """Query Github API to find the related object"""
        gh_api = self.get_github_connector()
        return gh_api.get_organization(obj_id or self.github_name)

    # Action section
    def button_sync_member(self):
        gh_org = self.find_related_github_object()
        partner_obj = self.env["res.partner"]
        for organization in self:
            member_ids = []
            for gh_member in gh_org.get_members():
                partner = partner_obj.get_from_id_or_create(gh_data=gh_member)
                member_ids.append(partner.id)
            organization.member_ids = member_ids

    def button_sync_repository(self):
        repository_obj = self.env["github.repository"]

        for organization in self:
            gh_api = self.get_github_connector()
            synced_count = 0
            last_cursor = organization.last_search_cursor
            limit = organization.repository_sync_limit or 20

            # Construir query para Search API
            query_parts = ["org:%s" % organization.github_name]

            # Filtro por topics: primer topic va en la query (AND servidor)
            extra_topics = []
            if organization.sync_filter_topics:
                topics = [t.strip().lower() for t in organization.sync_filter_topics.split(',') if t.strip()]
                if topics:
                    query_parts.append("topic:%s" % topics[0])
                    extra_topics = topics[1:]  # Los demás se filtran localmente (OR)

            # Filtro por fecha (si tenemos cursor)
            if last_cursor:
                date_str = last_cursor.strftime("%Y-%m-%dT%H:%M:%S")
                query_parts.append("pushed:>%s" % date_str)

            query = " ".join(query_parts)
            _logger.warning(
                "GITHUB SYNC: Org=[%s] Query=[%s] Limit=[%d]",
                organization.github_name, query, limit
            )

            # Search API no soporta sort=pushed, así que ordenamos localmente
            search_results = list(gh_api.search_repositories(query=query))
            search_results.sort(key=lambda r: r.pushed_at or datetime.min)

            _logger.warning(
                "GITHUB SYNC: Found %d repos matching query.", len(search_results)
            )

            for gh_repo in search_results:
                repo_pushed = gh_repo.pushed_at.replace(tzinfo=None) if gh_repo.pushed_at else None

                # Filtro local por topics extras (OR entre sí)
                if extra_topics:
                    repo_topics = [t.lower() for t in (gh_repo.topics or [])]
                    if not any(et in repo_topics for et in extra_topics):
                        continue

                _logger.warning(
                    "GITHUB SYNC: Syncing repo [%s] pushed=[%s]",
                    gh_repo.name, repo_pushed
                )

                # 1. Crear/Actualizar el registro en Odoo
                repository = repository_obj.with_context(
                    github_organization_id=organization.id
                ).get_from_id_or_create(gh_data=gh_repo)

                # 2. Actualizar datos y sincronizar ramas
                data = repository.get_odoo_data_from_github(gh_repo)
                repository._update_from_github_data(data)
                repository.button_sync_branch()
                repository.write({'github_last_sync_date': fields.Datetime.now()})

                # 3. Actualizar cursor
                if repo_pushed:
                    organization.last_search_cursor = repo_pushed

                # 4. Control de Batch
                synced_count += 1
                if synced_count >= limit:
                    _logger.warning("GITHUB SYNC: Batch limit reached (%d). Stopping.", synced_count)
                    break

            _logger.warning("GITHUB SYNC: Finished. Synced %d repos.", synced_count)

    def button_sync_team(self):
        gh_org = self.find_related_github_object()
        team_obj = self.env["github.team"]
        for organization in self:
            try:
                team_ids = []
                for gh_team in gh_org.get_teams():
                    team = team_obj.get_from_id_or_create(
                        gh_data=gh_team, extra_data={"organization_id": organization.id}
                    )
                    team_ids.append(team.id)
                organization.team_ids = team_ids
            except GithubException as e:
                if e.status == 403:
                    raise exceptions.AccessError(
                        _(
                            "The provided Github Token must have admin read:org"
                            " permissions to the organization '%s'"
                        )
                        % self.name
                    ) from None

    def action_github_repository(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "github_connector.action_github_repository"
        )
        action["context"] = dict(self.env.context)
        action["context"].pop("group_by", None)
        action["context"]["search_default_organization_id"] = self.id
        return action

    def action_github_team(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "github_connector.action_github_team"
        )
        action["context"] = dict(self.env.context)
        action["context"].pop("group_by", None)
        action["context"]["search_default_organization_id"] = self.id
        return action

    def action_res_partner(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "github_connector.action_res_partner"
        )
        action["context"] = dict(self.env.context)
        action["context"].pop("group_by", None)
        action["context"]["search_default_organization_ids"] = self.id
        return action
