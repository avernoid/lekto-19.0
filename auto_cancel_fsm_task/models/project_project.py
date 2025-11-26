from odoo import models, fields, _

class ProjectProject(models.Model):
    _inherit = 'project.project'

    antiquity_in_hours = fields.Float(
        string="Antiguedad en Horas",
        help="Hours to consider a task old relative to its end date."
    )

    def action_manually_run_cron(self):
        self.ensure_one()
        # Filter tasks for this project specifically
        self.env['project.task']._cron_auto_cancel_tasks(project_id=self.id)
