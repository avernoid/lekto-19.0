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
        domain = [
            ('state', 'not in', ['1_done', '1_canceled']),
            ('active', '=', True),
            ('project_id.antiquity_in_hours', '!=', 0),
            ('date_deadline', '!=', False),
        ]
        
        if project_id:
            domain.append(('project_id', '=', project_id))

        tasks = self.search(domain)
        
        for task in tasks:
            limit_date = fields.Datetime.now() - timedelta(hours=task.project_id.antiquity_in_hours)
            if task.date_deadline < limit_date:
                task.write({
                    'state': '1_done',
                    'not_executed': True
                })
