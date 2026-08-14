from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Value we add to the native ``category`` selection of mail.activity.type.
#
# WHY reuse ``category`` instead of a brand-new boolean/field:
# ``category`` is Odoo's own extension point for "this activity type triggers a
# special behaviour".  The core already ships 'upload_file' and 'phonecall'
# there (mail/models/mail_activity_type.py) and branches on them across the
# activity UI.  Adding one more value keeps our feature *inside* the native
# concept ("an activity type with a special action") rather than bolting a
# parallel flag next to it -- so the plan line needs NO new field: it just
# points at this activity type like any other.
CATEGORY_SEND_MAIL = "send_mail"

# Rough day-equivalents, used ONLY to answer "does this chaining loop move the
# deadline forward at all?".  It is a guardrail, not a calendar simulator: the
# exact length of a month is irrelevant to the sign of the total.
DELAY_UNIT_DAYS = {"days": 1, "weeks": 7, "months": 30}


class MailActivityType(models.Model):
    """Let an activity type mean 'schedule an email', reusing native pieces.

    The activity type already owns ``mail_template_ids`` natively -- that is the
    field the chatter uses to offer the manual *Preview / Send Now* buttons.  We
    do not add a template field of our own; we simply reinterpret that existing
    one: when ``category == 'send_mail'`` the (single) template is what gets
    *scheduled* instead of merely offered as a button.

    Everything about the *when* (the delay) stays on the Activity Plan line
    (``mail.activity.plan.template`` -> delay_count / delay_unit / delay_from),
    which already computes a deadline date.  The only thing the plan line cannot
    express is a time-of-day, so we add ``send_mail_hour`` here.
    """

    _inherit = "mail.activity.type"

    # -- category extension ------------------------------------------------

    category = fields.Selection(
        selection_add=[(CATEGORY_SEND_MAIL, "Send Email (scheduled)")],
        ondelete={CATEGORY_SEND_MAIL: "set default"},
    )

    # -- time-of-day for the scheduled send --------------------------------

    # The Activity Plan computes the due *date* only (see
    # mail/models/mail_activity_plan_template.py::_get_date_deadline, which
    # returns a date, not a datetime).  A scheduled email needs a full instant,
    # and mail.scheduled.message even *rejects* a date in the past
    # (_check_scheduled_date).  So we need an explicit hour.
    #
    # WHY a fixed configurable hour (and not "the launch time" or "midnight"):
    # emails should leave at a predictable, business-friendly moment.  Using the
    # plan-launch time would make the send hour depend on when someone happened
    # to click; midnight sends look odd to recipients.  A per-type hour keeps
    # the choice next to the template it belongs to and is trivially auditable.
    send_mail_hour = fields.Float(
        string="Send At (hour)",
        default=8.0,
        help="Local time of day (24h, e.g. 8.5 = 08:30) at which the scheduled "
             "email leaves on its due date. Only used when the action is "
             "'Send Email (scheduled)'. If the resulting instant is already in "
             "the past it is clamped to 'now' so the send is never rejected.",
    )

    @api.constrains("category", "mail_template_ids", "res_model")
    def _check_send_mail_requirements(self):
        """A 'send_mail' type must resolve to exactly one template on a model.

        WHY enforce *exactly one*: ``mail_template_ids`` is a many2many for the
        native manual-button use case (offer several templates to pick from).
        But an automatic scheduled send has to pick ONE unambiguously -- there is
        no user in the loop to choose.  Rather than silently taking the first, we
        make the configuration explicit so a misconfigured type fails loudly at
        setup time, not silently at send time.
        """
        for activity_type in self.filtered(lambda t: t.category == CATEGORY_SEND_MAIL):
            if not activity_type.res_model:
                raise ValidationError(_(
                    "Activity type '%(name)s' is set to 'Send Email (scheduled)' "
                    "but has no model. A template always belongs to a model, so "
                    "the activity type needs one too.",
                    name=activity_type.name,
                ))
            if len(activity_type.mail_template_ids) != 1:
                raise ValidationError(_(
                    "Activity type '%(name)s' is set to 'Send Email (scheduled)' "
                    "and must reference exactly one email template (found %(n)s). "
                    "The scheduled send has no user to choose between several.",
                    name=activity_type.name,
                    n=len(activity_type.mail_template_ids),
                ))

    @api.constrains(
        "category", "chaining_type", "triggered_next_type_id",
        "delay_count", "delay_unit",
    )
    def _check_send_mail_chain_advances(self):
        """Refuse a chaining loop that never moves its deadline forward.

        WHAT WENT WRONG IN PRODUCTION: a 'send_mail' type whose "Trigger Next
        Activity" pointed back at itself with "-2 days after the deadline".
        Each chained activity was therefore born 2 days MORE overdue than the
        previous one.  Our send clamps a past instant to now+1min, the native
        cron posts it, the auto-done creates the next link -- also overdue --
        and the record received one email per minute, endlessly.

        Chaining an activity to itself is a legitimate, useful pattern (a
        recurring follow-up), so we do not forbid it.  What we forbid is a loop
        that does not ADVANCE: if the sum of the delays around the cycle is zero
        or negative, every completion re-triggers the chain instantly and no
        human can ever get ahead of it.

        Only loops containing a 'send_mail' type are checked: without an
        automatic completion the loop still needs a human to mark each activity
        done, so it self-throttles.  It is our auto-done that closes the circuit
        and makes it explosive -- so we own the guardrail.

        This is the CONFIGURATION half of the protection (fail loudly at setup
        time, like _check_send_mail_requirements above).  The RUNTIME half lives
        in mail_activity_mixin._schedule_activity_email, and catches loops this
        constraint cannot see -- ones assembled through paths that never write
        an activity type, such as Automation Rules recreating the activity.
        """
        for activity_type in self:
            cycle = activity_type._chaining_cycle()
            if not any(a_type.category == CATEGORY_SEND_MAIL for a_type in cycle):
                continue
            advance = sum(
                DELAY_UNIT_DAYS.get(a_type.delay_unit, 1) * a_type.delay_count
                for a_type in cycle
            )
            if advance <= 0:
                raise ValidationError(_(
                    "The activity types %(cycle)s form a 'Trigger Next Activity' "
                    "loop that never moves forward in time (total delay: "
                    "%(advance)s day(s)), and at least one of them sends a "
                    "scheduled email. Every email would complete its activity, "
                    "which would immediately create the next one, and so on "
                    "endlessly. Give the loop a positive 'Schedule' delay.",
                    cycle=", ".join("'%s'" % a_type.name for a_type in cycle),
                    advance=advance,
                ))

    def _chaining_cycle(self):
        """Return the activity types forming the trigger loop reachable from self.

        Walks ``triggered_next_type_id`` (only meaningful while
        ``chaining_type == 'trigger'``, the native invariant) and returns the
        types from the first repeated one onwards -- i.e. the loop itself, not
        the tail that leads into it.  Returns an empty list when the chain ends.
        """
        self.ensure_one()
        path = []
        current = self
        while current and current.chaining_type == "trigger" and current.triggered_next_type_id:
            if current in path:
                return path[path.index(current):]
            path.append(current)
            current = current.triggered_next_type_id
        return []
