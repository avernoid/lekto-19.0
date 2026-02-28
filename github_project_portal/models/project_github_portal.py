import ast
import re
from datetime import datetime

import requests
from odoo.exceptions import UserError

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


_list_steps = [('1', '1. BACKLOG'), ('2', '2. DOING'), ('3', '3. REVIEW'), ('4', '4. TESTING'), ('5', ' 5. PROD.'), ('6', '6. DONE'), ('7', '7. CANCEL')]


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    by_steps = fields.Selection(_list_steps, string="Step or Stage", help="Current step in the GitFlow process.")


class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_priority = fields.Boolean(
        string="On-Call Ticket",
        default=False,
        help="Select here if this ticket is an urgent on-call issue for the developer (creates HOTFIX)."
    )
    repository_id = fields.Many2one(
        comodel_name="github.repository",
        string="Repository",
        index=True,
        ondelete="cascade",
        domain="[('should_show_in_project', '=', True)]",
        help="GitHub Repository linked to this task."
    )
    organization_id = fields.Many2one(
        comodel_name="github.organization",
        string="Organization",
        related="repository_id.organization_id",
        help="GitHub Organization."
    )
    repository_branch_id = fields.Many2one(
        comodel_name="github.repository.branch",
        string="Repository Branch",
        domain="[('organization_id', '=', organization_id),('repository_id', '=', repository_id)]",
        help="Base branch in GitHub where the development will start."
    )
    github_branch_name = fields.Char(string="Created Branch", help="Name of the branch created in GitHub for this task.")
    release_candidate_name = fields.Char(string='Release Candidate', help="Name of the Release Candidate tag.")
    release_name = fields.Char(string='Release', help="Name of the Final Release tag.")
    task_steps = fields.Selection(_list_steps, string="Step or Stage", help="Current step in the GitFlow process.")
    pr_dev_id = fields.Char(string="PR DEV", help="Pull Request ID for the Development branch.")
    pr_prod_id = fields.Char(string="PR PROD", help="Pull Request ID for the Production branch.")
    is_github_project = fields.Boolean(string='GitHub Task', help="Enable if this task should follow the GitHub GitFlow.")
    module_id = fields.Many2one(
        comodel_name="github.repository.module", 
        string="Module", 
        domain="[('repository_id', '=', repository_id), ('repo_branch_id', '=', repository_branch_id)]",
        copy=False,
        help="Odoo module assigned to this task. Validated against the repository structure."
    )

    def action_sync_repositories(self):
        """
        Action called by the refresh button next to repository_id.
        Syncs repositories for all configured organizations.
        """
        self.env['github.organization'].search([]).button_sync_repository()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.onchange('repository_id', 'repository_branch_id')
    def _onchange_repository_and_branch(self):
        if self.repository_id and self.repository_id.should_validate_module and self.repository_branch_id:
            self.repository_id.sync_repositories_per_branch(self.repository_branch_id)

    def copy(self, default=None):
        empty_fields = [
            'is_github_project',
            'pr_prod_id',
            'pr_dev_id',
            'task_steps',
            'release_name',
            'release_candidate_name',
            'github_branch_name',
            'repository_branch_id',
            'repository_id',
            'is_priority'
        ]
        result = super().copy(default)
        for field in empty_fields:
            result[field] = False
        return result

    def get_pull_request_id(self, owner, repo, pull_request_number):
        graphql_url = 'https://api.github.com/graphql'
        github_token = self.env['abstract.github.model'].get_github_token()
        query = """
        query($owner: String!, $repo: String!, $pull_number: Int!) {
          repository(owner: $owner, name: $repo) {
            pullRequest(number: $pull_number) {
              id
            }
          }
        }
        """
        variables = {
            'owner': owner,
            'repo': repo,
            'pull_number': pull_request_number
        }
        headers = {
            'Authorization': f'Bearer {github_token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(graphql_url, json={'query': query, 'variables': variables}, headers=headers)
        if response.status_code == 200:
            json_response = response.json()
            if json_response.get('errors'):
                raise UserError(_(f"Revert PR Error: Could not process the ID of the pull request to revert:\n"
                                  f" {json_response.get('errors')}"
                                  f" {json_response.get('message')}."))
            return json_response['data']['repository']['pullRequest']['id']
        else:
            raise UserError(_(f"Revert PR Error: Could not find the ID of the pull request to revert:  {response.status_code}. {response.text}."))

    def revert_pull_request(self, pr_number):
        graphql_url = 'https://api.github.com/graphql'
        github_token = self.env['abstract.github.model'].get_github_token()
        pull_request_id = self.get_pull_request_id(self.organization_id.github_name, self.repository_id.name, pr_number)
        mutation = """
        mutation ($input: RevertPullRequestInput!) {
          revertPullRequest(input: $input) {
            pullRequest {
              id
              title
              state
            }
          }
        }
        """

        variables = {
            'input': {
                'pullRequestId': pull_request_id,
            }
        }
        headers = {
            'Authorization': f'Bearer {github_token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(graphql_url, json={'query': mutation, 'variables': variables}, headers=headers)
        if response.status_code != 200:
            raise UserError(_(f"Revert PR Error: Could not revert the pull request:  {response.status_code}. {response.text}."))

    def revert_pr_dev(self):
        if not self.pr_dev_id:
            raise UserError(_(f"Revert PR Error: PR DEV field is empty"))
        if not self.github_branch_name:
            raise UserError(_(f"Revert PR Error: Created Branch field is empty"))
        self.revert_pull_request(int(self.pr_dev_id))
        revert_branch = f'revert-{self.pr_dev_id}-{self.github_branch_name}'
        repository_id = self._connection_github_repo()
        existing_pulls = list(
            repository_id.get_pulls(base=self.repository_branch_id.name, head=f'{self.organization_id.github_name}:{revert_branch}', state='open'))
        if existing_pulls:
            revert_pr_id = existing_pulls[0]
            revert_pr_id.merge(merge_method='squash', commit_message=revert_pr_id.body)
            body_extra = f'<p><b>NOTE:</b> The branch {revert_branch} has been deleted </p>'
            self.add_message_task_pull_request(revert_pr_id, revert_branch, self.repository_branch_id.name, pr_state='rollback dev closed',
                                               add_body=body_extra)
            self._delete_branch(revert_branch)
        else:
            raise UserError(_("GitFlow Error: Could not find the pull request to revert. Contact system administrator."))

    @api.model
    def get_task_url(self, task_id):
        """Genera la URL de la tarea en Odoo."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/web#id={task_id}&view_type=form&model=project.task"
    
    def write(self, vals):
        github_flow = False
        for task in self:
            if vals.get('stage_id'):
                vals['task_steps'] = self.env['project.task.type'].browse(vals.get('stage_id')).by_steps

                if vals['task_steps'] in ['2', '3', '4', '5'] and task.module_id and task.repository_branch_id and task.repository_id.should_validate_module:
                    # valida si se esta trabajando con un modulo de la misma rama
                    existing_task = self.env['project.task'].search([
                        ('id', '!=', task.id), 
                        ('module_id', '=', task.module_id.id),
                        ('repository_branch_id', '=', task.repository_branch_id.id),
                        ('task_steps', 'in', ['2', '3', '4', '5']) 
                    ], limit=1)  
                    if existing_task:
                        task_url = self.get_task_url(existing_task.id)
                        raise UserError(f"A ticket for this module is already in process \n{task_url}")

            if vals.get('task_steps') and vals.get('is_github_project', task.is_github_project):
                # validar si se retrocede a algun stage anterior
                github_flow = True
                if int(vals.get('task_steps', '0')) < int(task.stage_id.by_steps):
                    if task.stage_id.by_steps in ['6', '7']:
                        raise UserError("GitFlow Error: After closing or cancelling a task, you cannot go back to an initial state. Create a new task.")
                    if task.stage_id.by_steps == '5':
                        raise UserError(_("GitFlow Error: After deploying to production, you cannot go back to a previous state. "
                                          "Create a new task with necessary documentation."))
                    elif task.stage_id.by_steps == '4':
                        if vals.get('task_steps') == '3':
                            raise UserError(_("GitFlow Error: After deploying to the development branch, you must return to Backlog or Doing."))
                        else:
                            self.revert_pr_dev()
                else:
                    if vals.get('task_steps', '0') != '7':
                        if int(task.stage_id.by_steps) + 1 != int(vals.get('task_steps')):
                            state_id = list(filter(lambda x: x[0] == f'{int(task.stage_id.by_steps) + 1}', _list_steps))[0][1]
                            bad_state_id = list(filter(lambda x: x[0] == vals.get('task_steps'), _list_steps))[0][1]
                            raise UserError(_(
                                f"GitFlow Error: You must follow the established order, you cannot skip to state {bad_state_id}. "
                                f"The next state should be {state_id}"
                            ))
                        else:
                            repository_branch_id = vals.get('repository_branch_id', task.repository_branch_id)
                            repository_id = vals.get('repository_id', task.repository_id)
                            if not repository_id or not repository_branch_id:
                                raise UserError(_(f"GitFlow Error: You must select a repository and a base branch"))
        result = super(ProjectTask, self).write(vals)
        if github_flow:
            for task in self:
                if task.is_github_project:
                    task.github_next_stage()
        return result

    def github_next_stage(self):
        if self.task_steps == '1':
            if self.github_branch_name:
                self._delete_branch(self.github_branch_name)
                self.github_branch_name = False
        elif self.task_steps == '2':
            if not self.github_branch_name and self.repository_id and self.repository_branch_id:
                self._create_branch()

        elif self.task_steps == '3':
            if self.github_branch_name:
                self._review_branch()

        elif self.task_steps == '4':
            if self.github_branch_name:
                self._review_to_test_branch()

        elif self.task_steps == '5':
            if self.github_branch_name:
                self._test_to_prod_branch()

        elif self.task_steps in ['6', '7']:
            if self.github_branch_name:
                self._delete_branch(self.github_branch_name)
                self.github_branch_name = False

    def get_id_from_task(self):
        task_id = ''.join(re.findall(r'NewId_(\d+)|(\d+)', str(self.id))[0])
        return task_id

    def _create_branch(self):
        repo = self._connection_github_repo()
        task_id = self.get_id_from_task()
        iniciales = ''.join([word[0] for word in self.repository_id.name.split('_')]).upper()
        level = 'HOTFIX' if self.is_priority else 'FIX'
        new_branch = "%s_%s%s" % (level, task_id, iniciales)
        self.repository_id._create_new_branch(repo, new_branch, self.repository_branch_id.name)
        body = f"Branch '{new_branch}' has been created in the repository"
        self.add_message_github(body)
        self.github_branch_name = new_branch

    def _connection_github_repo(self):
        repository_id = self.repository_id
        organization_id = self.organization_id
        gh_api = self._connection_github()
        org = gh_api.get_organization(organization_id.github_name)
        repo = org.get_repo(repository_id.name)
        return repo

    def _connection_github(self):
        return self.env['abstract.github.model'].get_github_connector()

    def add_message_github(self, body):
        # Enviar mensaje en el archivo
        partner = self.env['res.partner'].search([('id', '=', 1)])
        task_id = self.get_id_from_task()
        self.env['mail.message'].sudo().create([{
            'author_id': partner.id,  # Crear con usuario odoobot 1
            'model': 'project.task',
            'res_id': int(task_id),
            'date': datetime.now(),
            'message_type': 'notification',
            'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_comment'),
            'reply_to': False,
            'body': body
        }])

    def _delete_branch(self, branch_name, block=True):
        repo = self._connection_github_repo()
        try:
            repo.get_branch(branch_name)
            repo.get_git_ref(f"heads/{branch_name}").delete()
        except Exception as e:
            if block:
                raise UserError(_(f"Error: The branch {branch_name} does not exist in the repository: {e}"))

    def set_github_pr_label(self, pull_request_id, label_name):
        pull_request_id.add_to_labels(label_name)

    def get_create_pr_diff_files(self, repository_id, base_branch, head_branch):
        pr_diff_files = repository_id.compare(base_branch, head_branch)
        return pr_diff_files.files

    def get_edit_pr_diff_files(self, pull_request_id):
        diff_files = list(pull_request_id.get_files())
        return diff_files

    def get_pull_request_data(self, pr_diff_files):
        body_text = 'Modified files:\n'
        manifest_edit = False
        module_version = False
        module_name = False
        error_title = 'GITHUB ERROR - PR file validation'
        files_excluded = ['README.md', 'LICENSE', '.gitignore', 'requirements.txt']
        for diff_file in pr_diff_files:
            filename = diff_file.filename
            if filename in files_excluded:
                continue
            if not module_name:
                if self.repository_id.should_validate_module:
                    module_name = filename.split('/')[0]
                else:
                    module_name = self.repository_id.name
            if module_name not in filename and self.repository_id.should_validate_module:
                raise UserError(_(f"{error_title}: Changes found in more than one module, manually check the changes attempting to merge: \n"
                                  f" - {module_name}\n"
                                  f" - {filename.split('/')[0]}"))
            if '__manifest__.py' in filename:
                manifest_edit = True
                raw_url = diff_file.raw_url
                raw_url = raw_url.replace('/raw/', '/')
                raw_url = raw_url.replace('github.com', 'raw.githubusercontent.com')
                github_token = self.env['abstract.github.model'].get_github_token()
                headers = {"Authorization": f"Bearer {github_token}"}
                response = requests.get(raw_url, headers=headers)
                if response.status_code != 200:
                    raise UserError(_(f"GITHUB ERROR - PR file validation: {response.status_code}"))
                tmp_path = "/tmp/manifest_data.py"
                f = open(tmp_path, 'w')
                f.write(response.text)
                f.close()
                with open(tmp_path, 'r') as file:
                    content = file.read()
                    module_data = ast.literal_eval(content)
                    module_version = module_data['version']
                    if not module_data.get('module_type') or module_data.get('module_type', '') != 'official':
                        raise UserError(_(f"{error_title} Attribute module_type with value 'official' not found in __manifest__.py"))
                    file.close()
            body_text += f' - {diff_file.filename}\n'
        if not manifest_edit:
            raise UserError(_(f"{error_title}: __manifest__.py file modification not found"))
        return body_text, module_version, module_name

    def add_message_task_pull_request(self, pull_request_id, head_branch, base_branch, pr_state, add_body=''):
        html_message = f"<p>Pull request {pr_state}:</p>\n" \
                       f"<ul>\n" \
                       f"  <li><b>Source Branch: </b>{head_branch}</li>\n" \
                       f"  <li><b>Target Branch: </b>{base_branch}</li>\n" \
                       f"  <li><b>PR URL: </b><a href='{pull_request_id.html_url}'>{pull_request_id.html_url}</a></li>\n" \
                       f"</ul>"
        if add_body:
            html_message += f"\n{add_body}"
        self.add_message_github(html_message)

    def add_reviewer_team_to_pull_request(self, pull_request_id):
        review_team_id = self.env['github.team'].search([('is_review_team', '=', True)])
        if not review_team_id:
            raise UserError(_("Reviewer team not found, contact system administrator."))
        pull_request_id.create_review_request(team_reviewers=[review_team_id.github_name])

    def create_pull_request(self, repository_id, base_branch, head_branch, title, body, publish_msj, add_reviewer=True):
        github_pr = repository_id.create_pull(title=title, body=body, base=base_branch, head=head_branch)
        self.set_github_pr_label(github_pr, 'OdooGitHub')
        if add_reviewer:
            self.add_reviewer_team_to_pull_request(github_pr)
        if publish_msj:
            self.add_message_task_pull_request(github_pr, head_branch, base_branch, pr_state='created')
        return github_pr

    def update_pull_request(self, github_pr, head_branch, base_branch, title, body, publish_msj):
        github_pr.edit(title=title, body=body)
        self.add_reviewer_team_to_pull_request(github_pr)
        self.set_github_pr_label(github_pr, 'OdooGitHub')
        if publish_msj:
            self.add_message_task_pull_request(github_pr, head_branch, base_branch, pr_state='updated')

    def check_active_pull_requests(self, pull_request_ids):
        if len(pull_request_ids) > 1:
            flag = False
            for pull_request in pull_request_ids:
                if flag:
                    self.close_pull_request(pull_request)
                else:
                    flag = True

    def close_pull_request(self, github_pr):
        github_pr.edit(state='closed', body="Duplicate pull request, proceeding to close.")
        self.set_github_pr_label(github_pr, 'Duplicate')

    def check_pull_requests(self, base_branch, head_branch, publish_msj=True):
        repository_id = self._connection_github_repo()
        web_base_url = self.env['ir.config_parameter'].sudo().get_param('report.url')
        task_id = self.get_id_from_task()
        task_url = f"{web_base_url}/web#id={task_id}&view_type=form&model=project.task"
        pr_id = None
        existing_pulls = list(repository_id.get_pulls(base=base_branch, head=f'{self.organization_id.github_name}:{head_branch}', state='open'))
        if existing_pulls:
            pr_id = existing_pulls[0]
            diff_files = self.get_edit_pr_diff_files(pr_id)
        else:
            diff_files = self.get_create_pr_diff_files(repository_id, base_branch, head_branch)

        body, module_version, module_name = self.get_pull_request_data(diff_files)
        title = f'[FIX] {module_name} v{module_version}'
        body += f'\n**Task: {task_url}**\n'

        if existing_pulls and pr_id:
            self.update_pull_request(pr_id, head_branch, base_branch, title, body, publish_msj)
            self.check_active_pull_requests(existing_pulls)
        else:
            pr_id = self.create_pull_request(repository_id, base_branch, head_branch, title, body, publish_msj)
        return pr_id, module_name, module_version

    def _review_branch(self):
        try:
            if not self.is_priority:
                repo = self._connection_github_repo()
                prod_branch = self.repository_branch_id.name.split('-')[0] + '.0'
                diff_files = self.get_create_pr_diff_files(repo, prod_branch, self.github_branch_name)
                self.get_pull_request_data(diff_files)

                github_pr_id, module_name, module_version = self.check_pull_requests(self.repository_branch_id.name, self.github_branch_name)
                if self.release_candidate_name:
                    iteration = int(self.release_candidate_name.split('-')[-1]) + 1
                    rc_name = f'RC-{module_name}-{module_version}-{iteration}'
                    self._delete_branch(self.release_candidate_name, block=False)
                else:
                    rc_name = f'RC-{module_name}-{module_version}-1'
                self.check_tag_and_release(repo, rc_name)
                self.write({
                    'release_candidate_name': rc_name,
                    'pr_dev_id': str(github_pr_id.number)
                })
        except Exception as e:
            raise UserError(_("Review: Error creating pull request. Contact system administrator: %s" % e))

    def _review_to_test_branch(self):
        if not self.is_priority:
            try:
                repo = self._connection_github_repo()
                existing_pulls = list(
                    repo.get_pulls(base=self.repository_branch_id.name, head=f'{self.organization_id.github_name}:{self.github_branch_name}', state='open'))
                if existing_pulls:
                    github_pr_id = existing_pulls[0]
                    github_pr_id.merge(merge_method='squash', commit_title=github_pr_id.title, commit_message=github_pr_id.body)
                    branch_id = repo.get_branch(self.github_branch_name)
                    repo.create_git_tag_and_release(
                        tag=self.release_candidate_name, tag_message=github_pr_id.body,
                        release_name=self.release_candidate_name, release_message=github_pr_id.body,
                        object=branch_id.commit.sha, type='commit',
                        prerelease=True, generate_release_notes=True
                    )
                    tag_id = repo.get_git_ref(f"tags/{self.release_candidate_name}")
                    repo.create_git_ref(ref=f"refs/heads/{self.release_candidate_name}", sha=tag_id.object.sha)
                    self.add_message_task_pull_request(github_pr_id, self.github_branch_name, self.repository_branch_id.name, pr_state='closed')
                else:
                    raise UserError(_("No open pull request found. Contact system administrator."))
            except Exception as e:
                raise UserError(_("Testing: Error closing pull request: %s " % e))

    def _test_to_prod_branch(self):
        try:
            repository_id = self._connection_github_repo()
            prod_branch = self.repository_branch_id.name.split('-')[0] + '.0'
            github_pr_id, module_name, module_version = self.check_pull_requests(prod_branch, self.release_candidate_name, False)
            release_name = f'{module_name}-{module_version}'
            self.check_tag_and_release(repository_id, release_name)
            github_pr_id.merge(merge_method='squash', commit_title=github_pr_id.title, commit_message=github_pr_id.body)
            branch_id = repository_id.get_branch(prod_branch)
            repository_id.create_git_tag_and_release(
                tag=release_name, tag_message=github_pr_id.body,
                release_name=release_name, release_message=github_pr_id.body,
                object=branch_id.commit.sha, type='commit',
                prerelease=False, generate_release_notes=True
            )
            tag_id = repository_id.get_git_ref(f"tags/{release_name}")
            repository_id.create_git_ref(ref=f"refs/heads/{release_name}", sha=tag_id.object.sha)
            self.update_develop_with_main(repository_id, self.repository_branch_id.name, prod_branch)
            body_extra = f'<p><b>NOTE:</b> The branch {self.github_branch_name} has been deleted </p>'
            self.add_message_task_pull_request(github_pr_id, self.release_candidate_name, prod_branch, pr_state='Prod. closed', add_body=body_extra)
            self._delete_branch(self.github_branch_name)
            self._delete_branch(release_name)
            self._delete_branch(self.release_candidate_name)
            self.delete_rc_tag_and_release()
            self.write({
                'release_name': release_name,
                'pr_prod_id': str(github_pr_id.number),
                'github_branch_name': False
            })
        except Exception as e:
            raise UserError(_(f"Production: Error merging to production: {e}"))

    def delete_rc_tag_and_release(self):
        rc_name_split = self.release_candidate_name.split('-')
        rc_name = f'{rc_name_split[0]}-{rc_name_split[1]}-{rc_name_split[2]}'
        iteration = int(rc_name_split[-1])
        for i in range(iteration, 0, -1):
            tag_name = f'{rc_name}-{i}'
            try:
                repository_id = self._connection_github_repo()
                tag_ref = repository_id.get_git_ref(f"tags/{tag_name}")
                tag_ref.delete()
                release = repository_id.get_release(tag_name)
                if release:
                    release.delete_release()
                _logger.info(f"- {self.repository_id.name}: Tag and release {tag_name} deleted")
            except Exception as e:
                _logger.info(f"Tag and/or release {tag_name} not found to delete: {e}")

    @staticmethod
    def check_tag_and_release(repository_id, version_release_name):
        try:
            existing_tag = repository_id.get_git_ref(f"tags/{version_release_name}")
        except Exception:
            existing_tag = False
        try:
            existing_release = repository_id.get_release(version_release_name)
        except Exception:
            existing_release = False
        if existing_tag or existing_release:
            raise UserError(f"A tag and/or release with name '{version_release_name}' already exists. Please choose a different name.")

    @staticmethod
    def update_develop_with_main(repository_id, develop_branch, main_branch):
        try:
            main_ref = repository_id.get_git_ref(f"heads/{main_branch}")
            repository_id.merge(develop_branch, main_ref.object.sha, f"Merge {main_branch} into {develop_branch}")
        except Exception as e:
            raise UserError(f"Synchronization {develop_branch} {e}")
