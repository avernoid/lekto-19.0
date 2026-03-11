from odoo import _, fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    skip_wizard_on_sale = fields.Boolean(
        string="Skip Wizard If Sale Exists",
        default=False,
        help=(
            "Controls whether the stop-timer confirmation wizard is bypassed when the task "
            "already has a confirmed Sale Order.\n\n"
            "When enabled and a confirmed SO exists, time is logged automatically with the "
            "description 'Automated register'. The wizard never opens.\n\n"
            "When disabled or no SO exists, the native wizard opens normally."
        ),
    )

    auto_return_to_previous_view = fields.Boolean(
        string="Auto return to task list after stopping timer",
        default=False,
        help=(
            "When enabled, after stopping the timer the user is automatically navigated "
            "to the configured Return Action (or the FSM task list as fallback) instead of "
            "remaining on the task form.\n\n"
            "Works in both flows: bypass (no wizard) and wizard (Log Time).\n"
            "Navigation is a clean reload — no breadcrumbs are accumulated."
        ),
    )

    return_action_id = fields.Many2one(
        'ir.actions.act_window',
        string="Return Action",
        help=(
            "Action to execute after stopping the timer (when 'Auto return' is enabled). "
            "Leave empty to use the FSM task list of this project as fallback.\n\n"
            "Example: select 'My Tasks Today' to return the technician to their daily task view."
        ),
    )

    def _get_auto_return_action(self):
        """
        Build the navigation action for auto_return_to_previous_view.

        Returns an ir.actions dict with target='main' so Odoo performs
        a clean reload of the view — no breadcrumbs are accumulated.

        Priority:
        1. return_action_id (if configured)
        2. Fallback: generic FSM task list of this project
        """
        self.ensure_one()
        if self.return_action_id:
            action = self.return_action_id.read()[0]
            # 'main' replaces the entire view stack — clean navigation, no breadcrumbs
            action['target'] = 'main'
            return action

        # Fallback: list of FSM tasks for this project (clean reload)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tasks'),
            'res_model': 'project.task',
            'view_mode': 'list,kanban,form',
            'domain': [('project_id', '=', self.id), ('is_fsm', '=', True)],
            'context': {'fsm_mode': True, 'default_project_id': self.id},
            'target': 'main',
        }
