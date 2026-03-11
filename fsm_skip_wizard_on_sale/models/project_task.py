from odoo import _, models
import logging

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def _fsm_has_confirmed_sale(self):
        """
        Check if this FSM task has at least one confirmed Sale Order.
        Checks both task.sale_order_id and any SO linked via task_id domain.
        """
        if self.sale_order_id and self.sale_order_id.state in ('sale', 'done'):
            return True
        return bool(self.env['sale.order'].search([
            ('task_id', '=', self.id),
            ('state', 'in', ('sale', 'done')),
        ], limit=1))

    def action_timer_stop(self):
        """
        Override to bypass the confirmation wizard when:
        - The task is an FSM task
        - The project has 'skip_wizard_on_sale' enabled
        - The task has at least one confirmed sale order

        The native `project.task.action_timer_stop` (defined in timesheet_grid)
        finds the running timesheet and returns the wizard action directly,
        so the override must live HERE — not in account.analytic.line.

        Bypass strategy:
        1. Find the running timesheet for this user.
        2. Call account.analytic.line.action_timer_stop() to compute elapsed
           time and clean up the timer (this also handles the timesheet_grid
           rounding/minimum-duration logic).
        3. Write 'Automated register' as the timesheet name so it has a
           meaningful description (mirroring what the wizard would do).
        4. If project.auto_mark_done is enabled (from fsm_geofencing_control),
           mark the task as done — exactly as the wizard would have.
        5. Return False → frontend JS receives falsy result → no wizard opens.

        When bypass is NOT active, delegate to super() so the wizard opens
        exactly as in a standard Odoo installation.
        """
        self.ensure_one()
        project = self.project_id

        if (self.is_fsm
                and project.skip_wizard_on_sale
                and self._fsm_has_confirmed_sale()):

            timesheet = self._get_record_with_timer_running()
            if timesheet:
                # Stop timer via the analytic-line method to handle rounding /
                # minimum-duration / timer-cleanup (timesheet_grid logic).
                # This does NOT open the wizard because we call it directly.
                timesheet.action_timer_stop()

                # Re-query the resulting timesheet (the record may have been
                # merged or replaced by timesheet_grid's try_to_match logic).
                resulting = self.env['account.analytic.line'].search(
                    [('task_id', '=', self.id)], order='id desc', limit=1
                )
                if resulting and resulting.unit_amount > 0:
                    resulting.write({'name': _('Automated register')})
                    _logger.info(
                        "fsm_skip_wizard_on_sale: bypass active for task %s, "
                        "saved timesheet %s with 'Automated register'",
                        self.id, resulting.id,
                    )
                else:
                    _logger.info(
                        "fsm_skip_wizard_on_sale: bypass active for task %s, "
                        "zero-duration stop — timesheet unchanged",
                        self.id,
                    )

                # Honour auto_mark_done from fsm_geofencing_control.
                # When the wizard is bypassed, this project-level setting must
                # still be applied — since the wizard (which normally does this)
                # is never shown.
                auto_mark_done = getattr(project, 'auto_mark_done', False)
                if auto_mark_done:
                    self.write({'fsm_done': True, 'state': '1_done'})
                    _logger.info(
                        "fsm_skip_wizard_on_sale: auto_mark_done applied "
                        "for task %s (project %s)",
                        self.id, project.id,
                    )

                # Honour auto_return_to_previous_view from project settings.
                # _get_auto_return_action() returns the configured menu action
                # (or FSM task list fallback) with target='main' for a clean
                # reload that doesn't accumulate breadcrumbs.
                auto_return = getattr(project, 'auto_return_to_previous_view', False)
                if auto_return:
                    return_action = project._get_auto_return_action()
                    _logger.info(
                        "fsm_skip_wizard_on_sale: auto_return active for task %s — "
                        "returning action %s",
                        self.id, return_action.get('type'),
                    )
                    return return_action

                return False  # no wizard dialog, no navigation

        return super().action_timer_stop()

