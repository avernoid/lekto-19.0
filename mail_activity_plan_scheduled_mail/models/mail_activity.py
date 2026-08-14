from odoo import api, models

from .mail_activity_type import CATEGORY_SEND_MAIL


class MailActivity(models.Model):
    """Queue the email whenever a 'send_mail' activity is created -- any path.

    WHY hook ``create`` and not ``activity_schedule``:
    not every activity is born through ``activity_schedule``.  Activity
    *chaining* -- the activity type's "Trigger Next Activity" -- creates the
    next activity with a direct ``self.env['mail.activity'].create(...)`` inside
    ``mail/models/mail_activity.py::_action_done`` (the ``next_activities =
    self.env['mail.activity'].create(next_activities_values)`` line).  So a
    chained ``send_mail`` activity was created correctly but its email was never
    queued -- the gap this override closes.

    ``mail.activity.create`` is the single funnel EVERY creation path goes
    through: Activity Plans and Automation Rules reach it via
    ``activity_schedule`` (which ends in ``mail.activity.create``), chaining and
    manual "Schedule Activity" reach it directly.  Hooking here covers them all
    at once, with exactly one schedule per activity (no double-send) and no need
    to wrap several higher-level methods.

    Gated strictly on ``category == 'send_mail'`` (a value only this module
    introduces), so no pre-existing activity type or flow is affected.
    """

    _inherit = "mail.activity"

    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)
        for activity in activities:
            if activity.activity_type_id.category != CATEGORY_SEND_MAIL:
                continue
            if not (activity.res_model and activity.res_id):
                # An activity always targets a record; be defensive anyway so we
                # never break activity creation over a missing document.
                continue
            record = self.env[activity.res_model].browse(activity.res_id)
            # Only documents carrying our mixin can render/queue the email.
            # (Any model with activities inherits it, but stay defensive.)
            if hasattr(record, "_schedule_activity_email"):
                record._schedule_activity_email(activity)
        return activities
