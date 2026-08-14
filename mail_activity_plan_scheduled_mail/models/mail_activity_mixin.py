import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import fields, models

_logger = logging.getLogger(__name__)

# Context key we drop while creating the composer.  It rides -- untouched --
# all the way into the scheduled message and is read back when the message is
# finally posted (see mail_scheduled_message.py for the other half).
#
# WHY this exact mechanism works with zero overrides on the write path:
# mail/wizard/mail_compose_message.py::_action_schedule_message builds the
# mail.scheduled.message via _prepare_schedule_message_post_values(), and that
# method sets  'send_context': clean_context(self.env.context)  (mail 19,
# mail_compose_message.py ~line 742).  So any custom context key we pass to the
# composer is persisted on the scheduled message for free.  clean_context only
# strips 'default_*' keys (odoo/tools/misc.py::clean_context), so a key that
# does NOT start with 'default_' survives -- hence this name.
ACTIVITY_LINK_CTX_KEY = "plan_sent_activity_id"

# Flag raised while we auto-complete a scheduled send (see
# mail_scheduled_message.py).  It rides the context through
# ``mail.activity._action_done`` into the ``mail.activity.create`` that builds
# the CHAINED activity, so that new activity knows it was born from an automatic
# send rather than from a human or a plan launch.
#
# WHY it survives the trip: ``action_feedback`` re-enters ``_action_done`` with
# ``clean_context(self.env.context)``, and ``clean_context`` only strips
# ``default_*`` keys -- the same property the ACTIVITY_LINK_CTX_KEY above relies
# on.  ``_action_done`` then calls ``self.env['mail.activity'].create(...)`` in
# that very environment, so our hook in models/mail_activity.py sees the flag.
#
# What it is FOR: see ``_schedule_activity_email`` -- the runaway-loop guardrail.
CHAIN_AUTODONE_CTX_KEY = "plan_sent_from_autodone"


class MailActivityMixin(models.AbstractModel):
    """Host the "render + queue the email" behaviour on the document record.

    The decision of *when* to schedule lives in ``mail.activity.create`` (see
    models/mail_activity.py) -- the single funnel every activity is born
    through.  This mixin only knows *how*: render the activity type's template
    against the concrete record and hand it to the native composer.  Keeping the
    rendering here (on the document, which carries lang/tz/company) is what gives
    the email its correct context.
    """

    _inherit = "mail.activity.mixin"

    def _schedule_activity_email(self, activity):
        """Queue the activity's template as a native 'Send Later' message.

        We deliberately drive the real ``mail.compose.message`` instead of
        hand-building a mail.scheduled.message.  This is the whole point of the
        design discussion behind this module: the chatter's "Send Later" stores
        an already-rendered snapshot of the template (subject, body, recipients,
        attachments, sender, layout), because the composer renders the template
        BEFORE scheduling.  Reusing the composer therefore gives us full template
        fidelity for free and stays correct if Odoo changes how templates render.
        """
        self.ensure_one()
        activity_type = activity.activity_type_id
        template = activity_type.mail_template_ids[:1]
        if not template:
            # Guarded by _check_send_mail_requirements at config time, but keep
            # the runtime defensive: no template -> nothing to schedule, and we
            # must never break the plan launch over it.
            return

        target_instant = self._activity_email_target_instant(activity)

        # -- runaway-loop guardrail -------------------------------------------
        #
        # THE FAILURE THIS PREVENTS (seen in production): an activity type whose
        # "Trigger Next Activity" points back at itself with a delay that does
        # NOT move the deadline forward (e.g. "-2 days after the deadline").
        # Every chained activity is then born already overdue; our send clamps
        # the past instant to now+1min, the cron posts it a minute later, the
        # auto-done creates the next activity -- also overdue -- and the record
        # gets one email per minute, forever.
        #
        # The invariant we enforce: an activity CHAINED BY AN AUTOMATIC SEND
        # must be due in the future.  When the chain fires, "now" is the moment
        # the previous email left, so a next link that is already past means the
        # configuration does not advance in time -- the signature of the loop.
        #
        # WHY only for chained activities: a FIRST link may legitimately be born
        # overdue (a plan launched after the send hour, a 'before_plan_date'
        # offset).  That case must keep working -- it is what the clamp below is
        # for -- and it cannot run away because nothing re-creates it.
        #
        # WHY we skip the send instead of raising: the activity itself is
        # perfectly valid and must still be created (raising would break the
        # native _action_done mid-flight).  Leaving it open, unsent, both stops
        # the loop -- nothing auto-completes it, so no further link is born --
        # and leaves a visible symptom for whoever configured the chain.
        if self.env.context.get(CHAIN_AUTODONE_CTX_KEY) and target_instant <= fields.Datetime.now():
            _logger.warning(
                "Skipping the scheduled email of activity %s (type '%s') on %s(%s): it was "
                "chained by an automatic send but is already due in the past (%s). The chained "
                "activity type must move the deadline forward -- check its 'Schedule' delay "
                "(a zero or negative delay makes every send instantly trigger the next one).",
                activity.id, activity_type.name, activity.res_model, activity.res_id,
                target_instant,
            )
            return

        scheduled_date = self._activity_email_scheduled_date(
            activity, target_instant=target_instant
        )

        # Hand the composer a context WITHOUT transient '__*' keys.
        #
        # WHY: _action_schedule_message persists ``clean_context(env.context)``
        # into the JSON ``send_context`` field of the scheduled message.  The
        # ambient context can carry non-JSON-serialisable transient values --
        # notably base_automation's ``__action_done``, a dict keyed by
        # base.automation *records* (see base_automation._process, which does
        # ``automation_done[self] = ...``).  Persisting that blows up with
        # "keys must be str ... not base.automation" (json.dumps).  ``clean_context``
        # strips only ``default_*`` keys, not ``__*`` ones, so we drop them here.
        # This surfaces whenever the activity is scheduled from inside an
        # Automation Rule (server action "Create Activity"), not just from a plan.
        # Non-'__' keys (lang, tz, allowed_company_ids, ...) are kept so template
        # rendering is unchanged.  Replacing (not merging) the context also means
        # the outer automation's own ``__action_done`` loop-guard is untouched.
        #
        # CHAIN_AUTODONE_CTX_KEY is dropped too: it is a transient marker for the
        # guardrail above, meaningless once the message is queued, and we do not
        # want it persisted into send_context and replayed at posting time.
        safe_ctx = {
            k: v for k, v in self.env.context.items()
            if not k.startswith("__") and k != CHAIN_AUTODONE_CTX_KEY
        }
        safe_ctx[ACTIVITY_LINK_CTX_KEY] = activity.id

        # composition_mode='comment' + a single res_id == the exact mode
        # _action_schedule_message supports (it rejects mass/batch mode).
        composer = self.env["mail.compose.message"].with_context(safe_ctx).create({
            "composition_mode": "comment",
            "model": activity.res_model,
            "res_ids": repr([activity.res_id]),
            "template_id": template.id,
        })
        # Set the instant after creation so it wins over the template-derived
        # compute of ``scheduled_date`` (mail_compose_message.py:_compute_scheduled_date).
        composer.scheduled_date = scheduled_date
        # Creates the mail.scheduled.message (carrying our context in
        # send_context) and returns it; we don't need the record because the
        # link travels in send_context.
        composer._action_schedule_message()

    def _activity_email_target_instant(self, activity):
        """Turn the plan's due *date* + the type's hour into a UTC datetime.

        This is the instant the configuration ASKS for, with no correction
        applied -- which is exactly why it is split out of
        ``_activity_email_scheduled_date``: the runaway-loop guardrail has to
        judge the configured intent, and the clamp below would hide a deadline
        that is days in the past behind a friendly "now + 1 min".

        We interpret ``send_mail_hour`` in the current user's timezone (what an
        admin naturally means by "send at 8") and convert to the naive-UTC Odoo
        stores.
        """
        activity_type = activity.activity_type_id
        raw_hour = activity_type.send_mail_hour or 0.0
        hour = min(int(raw_hour), 23)
        minute = min(int(round((raw_hour - int(raw_hour)) * 60)), 59)

        user_tz = pytz.timezone(self.env.user.tz or "UTC")
        local_dt = user_tz.localize(
            datetime.combine(activity.date_deadline, time(hour=hour, minute=minute))
        )
        return local_dt.astimezone(pytz.utc).replace(tzinfo=None)

    def _activity_email_scheduled_date(self, activity, target_instant=None):
        """The instant above as the string mail.scheduled.message accepts.

        ``mail.scheduled.message`` forbids a date in the past
        (_check_scheduled_date), and a legitimate first send can be born overdue
        (a 'before_plan_date' offset, or a plan launched after the send hour), so
        a past instant is clamped to just-after-now instead of being rejected.
        """
        utc_dt = target_instant or self._activity_email_target_instant(activity)
        now = fields.Datetime.now()
        if utc_dt <= now:
            utc_dt = now + timedelta(minutes=1)
        return fields.Datetime.to_string(utc_dt)
