from odoo import fields, models, _

class Task(models.Model):
    _inherit = "project.task"

    lost_reason_id = fields.Many2one(
        'sale.lost.reason',
        string='Lost Reason',
        help="Reason why the sale was lost.",
        copy=False
    )

    def _check_lost_reason_required(self):
        """
        Check if the lost reason wizard should be triggered.
        Returns True if the wizard is required, False otherwise.
        """
        self.ensure_one()
        # Condition 1: Project has "Use Lost Reason" enabled
        if not self.project_id.use_lost_reason:
            return False

        # Condition 2: Task is moving to "1_done" (This check is usually done before calling this method
        # or implied by the button calling it, but we can double check if needed,
        # though here we assume we are in the context of validating the task)

        # Condition 3: No confirmed Sale Order associated
        # We check if there are any sale orders linked to the task that are in 'sale' or 'done' state.
        # The user mentioned "action_fsm_view_material" button logic.
        # Usually, FSM tasks link to SOs via sale_order_id or sale_line_id.order_id.
        # We will check the standard sale_order_id field on the task.
        if self.sale_order_id and self.sale_order_id.state in ['sale', 'done']:
            return False
        
        # Also check if there are any other SOs linked (sometimes FSM creates multiple)
        # But usually the main one is sufficient. If the user specifically mentioned the smart button,
        # that usually filters by task_id.
        # Let's check if there are any orders linked to this task that are confirmed.
        sale_orders = self.env['sale.order'].search([('task_id', '=', self.id), ('state', 'in', ['sale', 'done'])])
        if sale_orders:
            return False

        return True

    def action_fsm_validate(self):
        """
        Override the standard FSM validate action to check for lost reason.
        """
        for task in self:
            if task._check_lost_reason_required() and not task.lost_reason_id:
                return {
                    'name': _('Lost Reason Required'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'project.task.lost.reason.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_task_id': task.id,
                        'active_id': task.id,
                        'active_model': 'project.task',
                    }
                }
        
        if self.env.context.get('skip_fsm_super'):
            return True

        return super().action_fsm_validate()
