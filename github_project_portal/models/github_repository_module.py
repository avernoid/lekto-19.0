from odoo import fields, models
from odoo.exceptions import UserError
import logging
# TODO: Eliminar archivo despues de eliminar los modulos agrupados en repositorios


_logger = logging.getLogger(__name__)

class GitHubRepositoryModule(models.Model):
    _name = 'github.repository.module'
    _description = 'GitHub Repository Modules'

    name = fields.Char(string='Module Name', required=True, help="Technical name of the module.")
    repository_id = fields.Many2one('github.repository', string='Repository', required=True, help="Related GitHub Repository.")
    url_repository = fields.Char(string='URL', related='repository_id.github_url', required=True, help="URL of the repository.")
    repo_branch_id = fields.Many2one('github.repository.branch', string='Repository Branch', help="Branch where this module is present.")
    organization_serie_id = fields.Many2one('github.organization.serie', string='Org Branch', store=True, related='repo_branch_id.organization_serie_id', help="Organization Serie/Branch.")
    organization_id = fields.Many2one(
        comodel_name="github.organization",
        string="Organization",
        related="repository_id.organization_id",
        help="Related GitHub Organization."
    )


class GitHubRepositoryBranch(models.Model):
    _inherit = 'github.repository.branch'
    _rec_name = 'complete_name'

    modules_ids = fields.One2many(comodel_name='github.repository.module', inverse_name='repo_branch_id', string='Modules', help="Modules contained in this branch.")


class GitHubRepository(models.Model):
    _inherit = 'github.repository'

    should_validate_module = fields.Boolean(string='Validate Modules', default=False, help="If set, enforces module validation logic on PRs.")
    should_show_in_project = fields.Boolean(string='Show in Projects', default=True, help="If set, this repository can be selected in Odoo Projects.")

    def button_sync_branch(self):
        super().button_sync_branch()
        for repository in self.filtered(lambda r: not r.is_ignored and r.should_validate_module):
            for branch in repository.repository_branch_ids:
                self.sync_repositories_per_branch(branch)

    def sync_repositories_per_branch(self, branch_id):
        self.ensure_one()
        repo = self.find_related_github_object()
        organization_id = self.organization_id
        try:
            # Obtener el contenido de la rama específica
            branch = repo.get_branch(branch_id.name)
            contents = repo.get_contents("", ref=branch.commit.sha)
            module_names = []
            for content in contents:
                if content.type == 'dir':
                    # Se obtiene el archivo __manifest__.py
                    try:
                        _ = repo.get_contents(f"{content.path}/__manifest__.py", ref=branch.commit.sha)
                        module_names.append(content.name)
                    except Exception as e:
                        _logger.warning(f"No se encontro el archivo __manifest__.py en {content.name}: {str(e)}")
                        pass
            repo_branch_id = self.env['github.repository.branch'].search([
                ('repository_id', '=', self.id),
                ('organization_serie_id', '=', branch_id.organization_serie_id.id),
                ('organization_id', '=', organization_id.id)
            ], limit=1)
            existing_modules = self.env['github.repository.module'].search([
                ('repository_id', '=', self.id),
                ('organization_serie_id', '=', branch_id.organization_serie_id.id),
                ('organization_id', '=', organization_id.id),
                ('repo_branch_id', '=', repo_branch_id.id)
            ])
            existing_module_names = existing_modules.mapped('name')
            # Filtra los nuevos módulos que no están ya en la base de datos
            new_modules = set(module_names) - set(existing_module_names)
            for module_name in new_modules:
                self.env['github.repository.module'].create({
                    'name': module_name,
                    'repository_id': self.id,
                    'organization_serie_id': branch_id.organization_serie_id.id,
                    'repo_branch_id': repo_branch_id.id
                })
        except Exception as e:
            raise UserError(f"Error al actualizar los módulos desde GitHub: {str(e)}")
