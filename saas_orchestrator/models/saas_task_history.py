from odoo import fields, models


class SaasTaskHistory(models.Model):
    _name = 'saas.task.history'
    _description = 'SaaS Control Plane Operation History'
    _order = 'created_at desc'

    instance_id = fields.Many2one('saas.instance', required=True, ondelete='cascade')
    operation_id = fields.Many2one(
        'saas.product.operation',
        ondelete='set null',
        help="Operation from the blueprint catalog executed by this task.",
    )
    task_type = fields.Char()
    payload = fields.Text()
    state = fields.Selection([
        ('queued', 'Queued'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='queued')
    result_summary = fields.Text()
    error_message = fields.Text()
    ssm_command_id = fields.Char(
        help="AWS SSM command id for traceability.",
    )
    orchestrator_task_id = fields.Char(
        index=True,
        help="UUID assigned by the orchestrator (primary key in orchestrator's tasks table).",
    )
    created_at = fields.Datetime(default=fields.Datetime.now)
    completed_at = fields.Datetime()
    duration_seconds = fields.Float()
