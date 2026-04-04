from odoo import models, fields, api
from datetime import timedelta

class ProjectTask(models.Model):
    _inherit = 'project.task'

    not_executed = fields.Boolean(
        string="No Ejecutada",
        default=False,
        copy=False,
        help=(
            "Indicates the visit was not carried out.\n"
            "Automatic behavior: set to True only by the Auto Cancel FSM cron when the "
            "project antiquity rule auto-completes the task.\n"
            "Manual behavior: users can set or unset it directly on Done tasks.\n"
            "Auto-reset behavior: when the task leaves Done, it is reset to False; when "
            "the task is completed by non-cron flows (for example, stopping timer), it "
            "remains False unless explicitly set by the user.\n"
            "This value is not copied when duplicating tasks."
        ),
    )

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
                task.with_context(from_auto_cancel_cron=True).write({
                    'state': '1_done',
                    'not_executed': True
                })

    def write(self, vals):
        """
        Keep `not_executed` strictly tied to auto-cancel flow.

        - Only the cron path can set `not_executed=True`.
        - Any non-cron transition to done clears stale `not_executed`.
        - Reopening a task also clears `not_executed`.
        """
        vals = dict(vals)
        state = vals.get('state')
        is_cron_flow = self.env.context.get('from_auto_cancel_cron')

        if state and state != '1_done' and 'not_executed' not in vals:
            vals['not_executed'] = False

        if state == '1_done' and not is_cron_flow and 'not_executed' not in vals:
            vals['not_executed'] = False

        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Prevent inherited/copied payloads from creating tasks already marked
        as not executed outside the cron flow.
        """
        is_cron_flow = self.env.context.get('from_auto_cancel_cron')
        sanitized = []
        for vals in vals_list:
            clean_vals = dict(vals)
            if clean_vals.get('not_executed') and not is_cron_flow:
                clean_vals['not_executed'] = False
            sanitized.append(clean_vals)
        return super().create(sanitized)
