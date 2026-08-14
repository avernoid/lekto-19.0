from odoo import _, models

from .mail_activity_mixin import ACTIVITY_LINK_CTX_KEY, CHAIN_AUTODONE_CTX_KEY


class MailScheduledMessage(models.Model):
    """Close the linked activity when its scheduled email is actually posted.

    This is the "auto-done" half of the feature, and it is intentionally hung on
    a *named* Odoo hook rather than on any send internals:

    ``mail.scheduled.message._message_created_hook(message)`` is called by
    ``_post_message`` right AFTER the delayed message has been posted -- and
    ``_post_message`` is what the native cron "Mail: Post scheduled messages"
    (``_post_messages_cron``) invokes on the due date.  See
    mail/models/mail_scheduled_message.py.  So overriding this hook means our
    activity is completed at the exact moment the email leaves, driven by the
    native queue, with no cron of our own.

    The activity id reaches us through ``send_context`` -- the JSON field the
    composer populated for us (see mail_activity_mixin.ACTIVITY_LINK_CTX_KEY for
    the full chain).  Its docstring in core literally describes it as the place
    to carry a "context used when posting the message to trigger some actions
    (eg. change some state when sending quotation)", so this is exactly its
    intended use.

    IMPORTANT ordering note: the base ``_message_created_hook`` is a plain
    ``ensure_one()`` no-op, but ``_post_message`` unlinks the scheduled message
    at the END of its loop.  We therefore read ``send_context`` from the record
    (still alive at hook time) and must not rely on it after ``_post_message``
    returns.
    """

    _inherit = "mail.scheduled.message"

    def _message_created_hook(self, message):
        res = super()._message_created_hook(message)
        for scheduled_message in self:
            activity_id = (scheduled_message.send_context or {}).get(ACTIVITY_LINK_CTX_KEY)
            if not activity_id:
                continue
            # ``.exists()`` because a user may have completed or deleted the
            # activity by hand before the send fired.  We deliberately do NOT
            # cancel the send in that case: the email was queued on purpose and
            # the activity was only ever a tracking marker for it.
            activity = self.env["mail.activity"].browse(activity_id).exists()
            if activity:
                # WHAT "done" actually means here (verified against
                # mail/models/mail_activity.py::_action_done): when the related
                # record still exists, completing an activity does NOT unlink it
                # -- it posts a 'mail.message_activity_done' message on the
                # record, stores the feedback, and ARCHIVES the activity
                # (active=False).  So the activity leaves the chatter's open
                # list exactly like a manual "Done", while its history survives.
                # (Only activities whose record was deleted get unlinked.)
                #
                # The context flag marks everything this completion sets off as
                # "born from an automatic send".  ``_action_done`` may create a
                # CHAINED activity ("Trigger Next Activity"), and that new
                # activity must be able to tell it was machine-made: an
                # automatically chained send that is already overdue is a
                # non-advancing loop, and our guardrail in
                # mail_activity_mixin._schedule_activity_email refuses to feed
                # it.  Without the flag the chain cannot be distinguished from a
                # legitimate late plan launch.
                activity.with_context(**{CHAIN_AUTODONE_CTX_KEY: True}).action_feedback(
                    feedback=_("Scheduled email sent automatically by its Activity Plan.")
                )
        return res
