from odoo import models, fields, _

class ProjectProject(models.Model):
    _inherit = 'project.project'

    antiquity_in_hours = fields.Float(
        string="Antiguedad en Horas",
        help=(
            "Project-level threshold in hours used by the daily Auto Cancel FSM cron.\n"
            "A task is auto-completed and marked as Not Executed only when all conditions are met:\n"
            "- The task is active and not in Done/Canceled\n"
            "- The task has an End Date\n"
            "- End Date is older than (current datetime - Antiquity in Hours)\n"
            "Set 0 to disable this automation for the project.\n"
            "The same logic can also be triggered manually with the Run Manually button."
        )
    )

    def action_manually_run_cron(self):
        self.ensure_one()
        # Filter tasks for this project specifically
        self.env['project.task']._cron_auto_cancel_tasks(project_id=self.id)
