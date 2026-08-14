import json
from datetime import date, timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestActivityPlanScheduledMail(TransactionCase):
    """End-to-end coverage of the 'send_mail' activity type.

    We schedule the activity directly via ``activity_schedule`` -- which is
    exactly the call an Activity Plan makes per line
    (mail/wizard/mail_activity_schedule.py::action_schedule_plan) -- so the test
    exercises the same seam a real plan launch would, without needing the whole
    plan UI.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # res.partner is the simplest carrier: it inherits mail.thread and the
        # activity mixin, and templates render fine against it.
        cls.partner = cls.env["res.partner"].create({"name": "Recipient Co"})

        cls.template = cls.env["mail.template"].create({
            "name": "Plan Reminder",
            "model_id": cls.env["ir.model"]._get("res.partner").id,
            "subject": "Hello {{ object.name }}",
            "body_html": "<p>Scheduled body for {{ object.name }}</p>",
            # partner_to so the posted message actually targets someone.
            "partner_to": "{{ object.id }}",
        })

        cls.send_type = cls.env["mail.activity.type"].create({
            "name": "Send Plan Reminder",
            "category": "send_mail",
            "res_model": "res.partner",
            "mail_template_ids": [(6, 0, cls.template.ids)],
            "send_mail_hour": 8.0,
        })

    def _schedule(self, days=3):
        """Schedule the send activity 'days' from today, as a plan line would."""
        return self.partner.activity_schedule(
            activity_type_id=self.send_type.id,
            automated=False,
            date_deadline=date.today() + timedelta(days=days),
        )

    def _scheduled_messages(self):
        return self.env["mail.scheduled.message"].search([
            ("model", "=", "res.partner"),
            ("res_id", "=", self.partner.id),
        ])

    # -- configuration guardrails -----------------------------------------

    def test_constraint_requires_exactly_one_template(self):
        """A send_mail type with zero or several templates must be rejected."""
        with self.assertRaises(ValidationError):
            self.send_type.mail_template_ids = [(5, 0, 0)]  # empty

        second = self.template.copy({"name": "Second"})
        with self.assertRaises(ValidationError):
            self.send_type.mail_template_ids = [(6, 0, (self.template + second).ids)]

    def test_constraint_requires_model(self):
        with self.assertRaises(ValidationError):
            self.env["mail.activity.type"].create({
                "name": "No model send",
                "category": "send_mail",
                "res_model": False,
                "mail_template_ids": [(6, 0, self.template.ids)],
            })

    # -- scheduling side effect -------------------------------------------

    def test_scheduling_creates_future_scheduled_message(self):
        """Scheduling the activity queues one future, linked scheduled message."""
        activity = self._schedule()

        messages = self._scheduled_messages()
        self.assertEqual(len(messages), 1, "Exactly one email should be queued")
        sched = messages

        # The link travels through send_context (composer -> scheduled message).
        self.assertEqual(
            (sched.send_context or {}).get("plan_sent_activity_id"),
            activity.id,
            "The scheduled message must remember which activity to close",
        )
        # It must be in the future (mail.scheduled.message forbids the past).
        self.assertTrue(sched.scheduled_date > fields.Datetime.now())
        # Full template fidelity: subject/body came from the rendered template.
        self.assertIn("Recipient Co", sched.subject)
        self.assertIn("Scheduled body", sched.body)
        self.assertIn(self.partner, sched.partner_ids)
        # The activity itself stays open until the email actually goes out.
        self.assertTrue(activity.exists())

    def test_posting_marks_activity_done(self):
        """When the queue posts the email, the linked activity is completed.

        'Completed' for an activity whose record still exists means ARCHIVED
        (active=False) with the feedback recorded and a done-message posted --
        NOT unlinked (see mail/models/mail_activity.py::_action_done). So we
        assert on ``active`` and ``feedback``, not on ``exists()``.
        """
        activity = self._schedule()
        sched = self._scheduled_messages()

        message_count_before = len(self.partner.message_ids)

        # Simulate the native cron firing on the due date. In tests
        # module.current_test is True, so _post_message skips its auto-commit.
        sched._post_message(raise_exception=True)

        # The activity is done: archived (gone from the open list) with feedback.
        self.assertTrue(activity.exists(), "History is kept, not deleted")
        self.assertFalse(activity.active, "Activity should be archived == done")
        self.assertIn("automatically", (activity.feedback or ""))
        # The email content was actually posted on the record.
        self.assertGreater(len(self.partner.message_ids), message_count_before)
        self.assertTrue(
            self.partner.message_ids.filtered(lambda m: "Scheduled body" in (m.body or "")),
            "The rendered template body should have been posted",
        )

    # -- real Activity Plan launch ----------------------------------------

    def test_launching_a_plan_schedules_the_email(self):
        """Full path: build a plan with a send_mail line and launch it.

        This drives the real ``mail.activity.schedule`` wizard the UI uses, so
        it proves the feature works through an actual Activity Plan and not only
        through a bare ``activity_schedule`` call.
        """
        plan = self.env["mail.activity.plan"].create({
            "name": "Onboarding emails",
            "res_model": "res.partner",
        })
        self.env["mail.activity.plan.template"].create({
            "plan_id": plan.id,
            "activity_type_id": self.send_type.id,
            "delay_count": 3,
            "delay_unit": "days",
            "delay_from": "after_plan_date",
            # 'other' + a concrete user avoids the "ask at launch" prompt.
            "responsible_type": "other",
            "responsible_id": self.env.user.id,
        })

        wizard = self.env["mail.activity.schedule"].with_context(
            active_model="res.partner",
            active_ids=self.partner.ids,
            active_id=self.partner.id,
        ).create({
            "res_model": "res.partner",
            "res_ids": repr(self.partner.ids),
            "plan_id": plan.id,
            "plan_on_demand_user_id": self.env.user.id,
        })
        wizard.action_schedule_plan()

        messages = self._scheduled_messages()
        self.assertEqual(len(messages), 1,
                         "Launching the plan should queue exactly one email")
        # And the activity created by the plan is the one the send is linked to.
        activity = self.partner.activity_ids.filtered(
            lambda a: a.activity_type_id == self.send_type
        )
        self.assertEqual(
            (messages.send_context or {}).get("plan_sent_activity_id"),
            activity.id,
        )

    # -- regression: creation paths other than activity_schedule ----------

    def test_scheduling_on_direct_activity_create(self):
        """A send_mail activity created directly (not via activity_schedule) also queues.

        This is the path activity chaining uses: _action_done creates the next
        activity with self.env['mail.activity'].create(...), bypassing
        activity_schedule. Hooking mail.activity.create covers it.
        """
        activity = self.env["mail.activity"].create({
            "activity_type_id": self.send_type.id,
            "res_model_id": self.env["ir.model"]._get("res.partner").id,
            "res_id": self.partner.id,
            "date_deadline": date.today() + timedelta(days=2),
        })
        sched = self._scheduled_messages()
        self.assertEqual(len(sched), 1, "Direct create must queue the email too")
        self.assertEqual(
            (sched.send_context or {}).get("plan_sent_activity_id"), activity.id
        )

    def test_chained_send_activity_also_schedules(self):
        """Trigger-chaining from one send activity to another queues BOTH emails.

        Reproduces the reported gap: activity #1 (send_mail) chains to activity
        #2 (also send_mail). When #1's email is posted it auto-completes and
        Odoo creates #2 via a direct mail.activity.create. #2's email must be
        queued as well.
        """
        template2 = self.template.copy({"name": "Second Reminder"})
        send_type_2 = self.env["mail.activity.type"].create({
            "name": "Send Follow-up",
            "category": "send_mail",
            "res_model": "res.partner",
            "mail_template_ids": [(6, 0, template2.ids)],
            "send_mail_hour": 9.0,
        })
        # Type #1 triggers type #2 when marked done.
        self.send_type.write({
            "chaining_type": "trigger",
            "triggered_next_type_id": send_type_2.id,
        })

        activity1 = self._schedule()
        first = self._scheduled_messages()
        self.assertEqual(len(first), 1)

        # Post #1's email -> auto-done -> Odoo creates the chained activity #2.
        first._post_message(raise_exception=True)

        # #2 exists and, crucially, its own email got queued.
        activity2 = self.partner.activity_ids.filtered(
            lambda a: a.activity_type_id == send_type_2
        )
        self.assertTrue(activity2, "The chained activity must be created")
        sched2 = self._scheduled_messages().filtered(
            lambda m: (m.send_context or {}).get("plan_sent_activity_id") == activity2.id
        )
        self.assertEqual(
            len(sched2), 1, "The chained send activity must queue its email too"
        )

    # -- runaway-loop guardrails ------------------------------------------

    def test_constraint_rejects_non_advancing_loop(self):
        """A send_mail type looping onto itself without advancing is rejected.

        Reproduces the production incident: "Trigger Next Activity" pointing at
        the type itself with '-2 days after the deadline'. Every chained
        activity is born more overdue than the last, so the send/auto-done pair
        re-fires immediately, forever.
        """
        with self.assertRaises(ValidationError):
            self.send_type.write({
                "chaining_type": "trigger",
                "triggered_next_type_id": self.send_type.id,
                "delay_count": -2,
                "delay_unit": "days",
                "delay_from": "previous_activity",
            })

        # A loop that stands still (delay 0) is just as explosive.
        with self.assertRaises(ValidationError):
            self.send_type.write({
                "chaining_type": "trigger",
                "triggered_next_type_id": self.send_type.id,
                "delay_count": 0,
            })

    def test_constraint_allows_advancing_loop(self):
        """A recurring reminder (positive delay) stays perfectly legal."""
        self.send_type.write({
            "chaining_type": "trigger",
            "triggered_next_type_id": self.send_type.id,
            "delay_count": 1,
            "delay_unit": "months",
            "delay_from": "previous_activity",
        })
        self.assertEqual(self.send_type.triggered_next_type_id, self.send_type)

    def test_recurring_loop_keeps_sending(self):
        """The guardrail must not break a legitimate self-chaining reminder.

        Type chains to itself +1 day: posting the first email completes the
        activity, Odoo creates the next link one day later, and that link's
        email must still be queued.
        """
        self.send_type.write({
            "chaining_type": "trigger",
            "triggered_next_type_id": self.send_type.id,
            "delay_count": 1,
            "delay_unit": "days",
            "delay_from": "previous_activity",
        })
        activity1 = self._schedule(days=3)
        first = self._scheduled_messages()
        self.assertEqual(len(first), 1)

        first._post_message(raise_exception=True)

        activity2 = self.partner.activity_ids.filtered(
            lambda a: a.activity_type_id == self.send_type
        )
        self.assertTrue(activity2, "The next link of the loop must be created")
        self.assertEqual(
            activity2.date_deadline, activity1.date_deadline + timedelta(days=1),
            "The loop advances one day per iteration",
        )
        self.assertTrue(
            self._scheduled_messages().filtered(
                lambda m: (m.send_context or {}).get("plan_sent_activity_id") == activity2.id
            ),
            "An advancing loop must keep queueing its emails",
        )

    def test_chained_activity_born_overdue_is_not_sent(self):
        """Runtime backstop: a machine-chained, already-overdue send is skipped.

        This is the state a non-advancing loop produces on every iteration. We
        reproduce it directly (the config constraint above blocks the setup, but
        the runtime guard must also hold for loops assembled through paths that
        never write an activity type). The activity is still created -- only the
        email is skipped, which is what breaks the cycle: with nothing to post,
        nothing auto-completes it, so no further link is ever born.
        """
        # assertLogs both proves the skip is reported to the admin and keeps the
        # expected warning out of ir.logging (it detaches the logger), so the
        # build stays clean.
        with self.assertLogs(
            "odoo.addons.mail_activity_plan_scheduled_mail.models.mail_activity_mixin",
            level="WARNING",
        ) as logs:
            activity = self.env["mail.activity"].with_context(
                plan_sent_from_autodone=True
            ).create({
                "activity_type_id": self.send_type.id,
                "res_model_id": self.env["ir.model"]._get("res.partner").id,
                "res_id": self.partner.id,
                "date_deadline": date.today() - timedelta(days=2),
            })
        self.assertTrue(any("Skipping the scheduled email" in m for m in logs.output))
        self.assertTrue(activity.exists(), "The activity itself is still created")
        self.assertFalse(
            self._scheduled_messages(),
            "An automatically chained activity born overdue must not send",
        )

    def test_first_link_born_overdue_still_sends(self):
        """The guard must NOT touch a legitimately late first send.

        A plan launched after the send hour, or a 'before_plan_date' offset,
        produces a past instant with no chain involved. That send is clamped to
        now+1min and must go out as before.
        """
        self.partner.activity_schedule(
            activity_type_id=self.send_type.id,
            automated=False,
            date_deadline=date.today() - timedelta(days=2),
        )
        sched = self._scheduled_messages()
        self.assertEqual(len(sched), 1, "A late first send is still queued")
        self.assertTrue(sched.scheduled_date > fields.Datetime.now())

    # -- regression: scheduling from an Automation Rule -------------------

    def test_scheduling_with_non_serialisable_context(self):
        """Scheduling must survive a context that holds record-keyed values.

        Reproduces the crash seen when an Automation Rule ('Create Activity')
        triggers our send: base_automation puts '__action_done' in the context,
        a dict keyed by base.automation *records*. The composer persists
        clean_context(env.context) into the JSON send_context field, so without
        stripping '__*' keys json.dumps raised
        "keys must be str ... not base.automation". Here we stand in a record for
        the automation to prove the value is dropped, not serialised.
        """
        poison = {"__action_done": {self.env.user: self.partner}}  # record-keyed
        activity = self.partner.with_context(**poison).activity_schedule(
            activity_type_id=self.send_type.id,
            automated=False,
            date_deadline=date.today() + timedelta(days=3),
        )

        sched = self._scheduled_messages()
        self.assertEqual(len(sched), 1, "The email is queued despite the context")
        # The transient key is gone; only our clean, JSON-safe link remains.
        self.assertNotIn("__action_done", (sched.send_context or {}))
        self.assertEqual(
            (sched.send_context or {}).get("plan_sent_activity_id"), activity.id
        )
        # And the whole thing round-trips through JSON without error.
        json.dumps(sched.send_context)

    # -- non-regression ----------------------------------------------------

    def test_normal_activity_type_unaffected(self):
        """A plain activity type must never queue an email."""
        normal = self.env["mail.activity.type"].create({
            "name": "Just a task",
            "res_model": "res.partner",
        })
        self.partner.activity_schedule(
            activity_type_id=normal.id,
            automated=False,
            date_deadline=date.today() + timedelta(days=2),
        )
        self.assertFalse(
            self._scheduled_messages(),
            "Only 'send_mail' types may schedule emails",
        )
