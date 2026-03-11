from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase


class TestFsmSkipWizardOnSale(TransactionCase):
    """
    Test the FSM timer stop bypass logic when skip_wizard_on_sale is enabled.

    IMPORTANT — entry point: The Stop button in the UI calls
    `project.task.action_timer_stop()` (defined in timesheet_grid), NOT
    `account.analytic.line.action_timer_stop()`. All tests use the task-level
    method to match the real UI flow.

    Expected behaviour:
    - skip_wizard_on_sale=False OR no confirmed SO → native open-wizard path:
      task.action_timer_stop() returns a dict (wizard action).
    - skip_wizard_on_sale=True AND confirmed SO → bypass path:
      task.action_timer_stop() returns False and writes 'Automated register'.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Use the canonical FSM project from industry_fsm fixtures
        cls.fsm_project = cls.env.ref('industry_fsm.fsm_project')
        cls.fsm_project.write({
            'allow_timesheets': True,
            'skip_wizard_on_sale': False,
        })

        # Customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer Skip Wizard',
        })

        # Employee linked to the current user (required for timesheets)
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee Skip Wizard',
            'user_id': cls.env.uid,
            'company_id': cls.env.company.id,
        })

        # Product for sale order lines
        cls.product = cls.env['product.product'].create({
            'name': 'Field Service Product',
            'type': 'service',
        })

    def _create_task(self):
        """Helper: create an FSM task linked to the test project and customer."""
        return self.env['project.task'].create({
            'name': 'Test Task Skip Wizard',
            'project_id': self.fsm_project.id,
            'partner_id': self.customer.id,
        })

    def _create_confirmed_sale_for_task(self, task):
        """Helper: create and confirm a Sale Order linked to the task."""
        sale = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'task_id': task.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        sale.action_confirm()
        return sale

    def _start_timer(self, task):
        """Helper: start the task timer."""
        task.action_timer_start()

    def _simulate_elapsed_time(self, task, minutes=30):
        """Back-date the running timesheet timer so elapsed time is non-zero.

        In test environments, timers start and stop almost instantaneously
        (0 s). timesheet_grid may then discard the record.  Moving the timer
        start into the past forces a non-zero unit_amount.

        The timer is linked to the account.analytic.line record, not the task.
        """
        timesheet = self.env['account.analytic.line'].search(
            [('task_id', '=', task.id)], order='id desc', limit=1
        )
        if not timesheet:
            self.fail("No timesheet found for task after timer start")
        timer = self.env['timer.timer'].sudo().search([
            ('res_model', '=', 'account.analytic.line'),
            ('res_id', '=', timesheet.id),
        ], limit=1)
        if timer:
            timer.timer_start = fields.Datetime.now() - timedelta(minutes=minutes)

    # ------------------------------------------------------------------ #
    # Tests                                                                #
    # ------------------------------------------------------------------ #

    def test_skip_disabled_returns_wizard_action(self):
        """
        When skip_wizard_on_sale is False, task.action_timer_stop should return
        a dict (the wizard action) — the standard Odoo 19 Enterprise behaviour.
        """
        self.fsm_project.write({'skip_wizard_on_sale': False})
        task = self._create_task()
        self._start_timer(task)
        self._simulate_elapsed_time(task, minutes=30)

        result = task.action_timer_stop()

        self.assertIsInstance(result, dict, "Should return a wizard action dict when bypass is disabled")
        self.assertEqual(result.get('res_model'), 'hr.timesheet.stop.timer.confirmation.wizard')

    def test_skip_enabled_no_sale_returns_wizard_action(self):
        """
        When skip_wizard_on_sale is True but NO confirmed sale exists,
        task.action_timer_stop should fall through and return the wizard action.
        """
        self.fsm_project.write({'skip_wizard_on_sale': True})
        task = self._create_task()  # No sale order
        self._start_timer(task)
        self._simulate_elapsed_time(task, minutes=30)

        result = task.action_timer_stop()

        self.assertIsInstance(result, dict, "Should return wizard action when no confirmed sale")
        self.assertEqual(result.get('res_model'), 'hr.timesheet.stop.timer.confirmation.wizard')

    def test_skip_enabled_with_confirmed_sale_bypasses_wizard(self):
        """
        When skip_wizard_on_sale is True AND a confirmed sale order exists,
        task.action_timer_stop should return False (bypass) and write
        'Automated register' as the timesheet description.
        """
        self.fsm_project.write({'skip_wizard_on_sale': True})
        task = self._create_task()
        self._create_confirmed_sale_for_task(task)
        self._start_timer(task)
        self._simulate_elapsed_time(task, minutes=30)

        result = task.action_timer_stop()

        self.assertFalse(result, "Should return False when bypass is triggered")

        resulting_timesheet = self.env['account.analytic.line'].search(
            [('task_id', '=', task.id)], order='id desc', limit=1
        )
        self.assertTrue(resulting_timesheet, "A completed timesheet should exist after stopping the timer")
        self.assertEqual(
            resulting_timesheet.name,
            'Automated register',
            "Timesheet description should be 'Automated register'"
        )

    def test_skip_with_draft_sale_returns_wizard_action(self):
        """
        A Sale Order in 'draft' state should NOT trigger the bypass.
        """
        self.fsm_project.write({'skip_wizard_on_sale': True})
        task = self._create_task()

        self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'task_id': task.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })  # NOT confirmed — state remains 'draft'

        self._start_timer(task)
        self._simulate_elapsed_time(task, minutes=30)

        result = task.action_timer_stop()

        self.assertIsInstance(result, dict, "Draft sale should NOT trigger bypass — native wizard action returned")

    def test_skip_with_cancelled_sale_returns_wizard_action(self):
        """
        A cancelled Sale Order should NOT trigger the bypass.
        """
        self.fsm_project.write({'skip_wizard_on_sale': True})
        task = self._create_task()

        sale = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'task_id': task.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        sale.action_cancel()

        self._start_timer(task)
        self._simulate_elapsed_time(task, minutes=30)

        result = task.action_timer_stop()

        self.assertIsInstance(result, dict, "Cancelled sale should NOT trigger bypass — native wizard action returned")

    def test_skip_on_non_fsm_task_not_triggered(self):
        """
        The bypass should never activate on non-FSM tasks, even if
        skip_wizard_on_sale is True on some project.
        """
        self.fsm_project.write({'skip_wizard_on_sale': True})

        non_fsm_project = self.env['project.project'].create({
            'name': 'Non FSM Project',
            'is_fsm': False,
            'allow_timesheets': True,
        })
        task = self.env['project.task'].create({
            'name': 'Non FSM Task',
            'project_id': non_fsm_project.id,
        })
        task.action_timer_start()
        self._simulate_elapsed_time(task, minutes=30)

        result = task.action_timer_stop()

        # Non-FSM tasks should never be bypassed — result is a wizard dict (or
        # False if no timer was running), but never our bypass False with name set.
        timesheet = self.env['account.analytic.line'].search(
            [('task_id', '=', task.id)], order='id desc', limit=1
        )
        if timesheet:
            self.assertNotEqual(
                timesheet.name, 'Automated register',
                "Non-FSM tasks should never get 'Automated register' name"
            )
