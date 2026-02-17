from odoo import models, fields, api
from datetime import timedelta

class ProjectTask(models.Model):
    _inherit = 'project.task'

    not_executed = fields.Boolean(string="No Ejecutada", default=False)

    @api.model
    def _cron_auto_cancel_tasks(self, project_id=None):
        """
        Cron job to automatically mark tasks as done if they exceed the antiquity limit.
        """
        # Search for projects with configured antiquity
        project_domain = [('antiquity_in_hours', '>', 0)]
        if project_id:
            project_domain.append(('id', '=', project_id))
            
        projects = self.env['project.project'].search(project_domain)
        
        for project in projects:
            # Calculate limit date based on project configuration
            limit_dt = fields.Datetime.now() - timedelta(hours=project.antiquity_in_hours)
            # Convert to date since date_deadline is a Date field
            limit_date = limit_dt.date()
            
            # Find tasks to cancel in batch for this project
            tasks_domain = [
                ('project_id', '=', project.id),
                ('state', 'not in', ['1_done', '1_canceled']),
                ('active', '=', True),
                ('date_deadline', '<', limit_date),
            ]
            tasks_to_cancel = self.search(tasks_domain)
            
            if tasks_to_cancel:
                tasks_to_cancel.write({
                    'state': '1_done',
                    'not_executed': True
                })
