# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def action_fsm_view_material(self):
        """Override to block access to the product catalog until the timer has
        been started, when the project requires it.

        The check covers two cases:
        - A ``timer.timer`` record for this task exists with ``timer_start``
          set and ``timer_pause`` empty (timer is running). We query the
          ``timer.timer`` model directly with sudo() using its stored fields,
          avoiding any dependency on computed/related fields on the task
          (``timer_start``, ``is_timer_running``) which are filtered by
          ``env.uid`` and may return stale cached values.
        - ``timesheet_ids``: at least one timesheet has been saved
          (Start+Stop already completed at least once).
        """
        self.ensure_one()

        if self.is_fsm and self.project_id.require_start_to_sell:
            active_timer = self.env['timer.timer'].sudo().search([
                ('res_model', '=', 'project.task'),
                ('res_id', '=', self.id),
                ('timer_start', '!=', False),
                ('timer_pause', '=', False),
            ], limit=1)
            if not active_timer and not self.sudo().timesheet_ids:
                raise UserError(_("You must start the task timer (Start button) before adding products or materials to this task."))

        return super().action_fsm_view_material()
