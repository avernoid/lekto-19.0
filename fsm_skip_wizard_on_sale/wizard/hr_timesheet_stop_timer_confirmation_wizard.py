from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)


class HrTimesheetStopTimerConfirmationWizard(models.Model):
    _inherit = 'hr.timesheet.stop.timer.confirmation.wizard'

    skip_wizard_on_sale = fields.Boolean(
        related="timesheet_id.project_id.skip_wizard_on_sale",
        readonly=True,
    )

    auto_return_to_previous_view = fields.Boolean(
        related="timesheet_id.project_id.auto_return_to_previous_view",
        readonly=True,
    )

    def action_save_timesheet(self):
        """
        Override to navigate back after saving the timesheet when
        auto_return_to_previous_view is enabled on the project.

        Calls super() first so the full chain runs:
          native action_save_timesheet
          → fsm_geofencing_control (auto_mark_done, distance, lost_reason)
          → this override (navigation decision)

        Uses project._get_auto_return_action() which returns:
          - The configured return_menu_id action  (if set)
          - FSM task list fallback                (if not set)
        Both with target='main' for a clean reload — no accumulated breadcrumbs.

        When a wizard (dialog) returns a non-close ir.actions.act_window with
        target='main', Odoo closes the dialog AND replaces the entire view stack
        with the returned action. No breadcrumbs are carried over.
        """
        project = self.timesheet_id.project_id

        # Full chain: native + fsm_geofencing_control (auto_mark_done etc.)
        result = super().action_save_timesheet()

        if getattr(project, 'auto_return_to_previous_view', False):
            return_action = project._get_auto_return_action()
            _logger.info(
                "fsm_skip_wizard_on_sale: auto_return active after wizard "
                "for project %s — returning action type=%s",
                project.id, return_action.get('type'),
            )
            return return_action

        return result
