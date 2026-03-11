from odoo import models
import logging

_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    # No overrides needed here.
    # The wizard bypass is handled in project.task.action_timer_stop,
    # which is the actual entry point called by the Stop button in the UI.
    # See models/project_task.py for the implementation.
