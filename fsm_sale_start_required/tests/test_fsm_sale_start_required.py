# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestFsmSaleStartRequired(TransactionCase):
    """Tests for the FSM Sale Start Required module.

    Scenarios covered:
    1. Block access when project requires start and no timer/timesheet exists.
    2. Allow access when an active timer exists (user_timer_id set).
    3. Allow access when timesheets exist (Start+Stop already done at least once).
    4. No block when project setting is disabled.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Find or create an FSM project
        cls.fsm_project = cls.env['project.project'].search(
            [('is_fsm', '=', True), ('company_id', '=', cls.env.ref('base.main_company').id)],
            limit=1,
        )
        if not cls.fsm_project:
            cls.fsm_project = cls.env['project.project'].create({
                'name': 'FSM Test Project (start_required)',
                'is_fsm': True,
                'allow_material': True,
                'allow_billable': True,
                'company_id': cls.env.ref('base.main_company').id,
            })
        else:
            cls.fsm_project.write({'allow_material': True})

        # Partner needed by action_fsm_view_material
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer SSR'})

        # Base task (no timer, no timesheets)
        cls.task = cls.env['project.task'].create({
            'name': 'Test Task SSR',
            'project_id': cls.fsm_project.id,
            'partner_id': cls.partner.id,
        })

    def setUp(self):
        super().setUp()
        # Reset the setting before each test to avoid inter-test contamination
        self.fsm_project.require_start_to_sell = False

    # ------------------------------------------------------------------
    # Test 1: Block when setting enabled and no timer/timesheets
    # ------------------------------------------------------------------
    def test_block_without_timer_or_timesheets(self):
        """UserError raised when require_start_to_sell=True and task not started."""
        self.fsm_project.require_start_to_sell = True

        with self.assertRaises(UserError, msg="Should raise UserError when no timer and no timesheets"):
            self.task.action_fsm_view_material()

    # ------------------------------------------------------------------
    # Test 2: Allow with active timer (user_timer_id present)
    # ------------------------------------------------------------------
    def test_allow_with_active_timer(self):
        """No error raised when an active timer exists on the task."""
        self.fsm_project.require_start_to_sell = True

        # Directly create a timer.timer record to simulate a running timer.
        # We avoid action_timer_start() because it may silently fail in test
        # environments where the user lacks a linked hr.employee (required by
        # FSM timesheet logic). Direct creation matches exactly what our
        # production search expects: timer_start set, timer_pause = False.
        timer = self.env['timer.timer'].create({
            'res_model': 'project.task',
            'res_id': self.task.id,
            'timer_start': fields.Datetime.now(),
            'timer_pause': False,
            'user_id': self.env.uid,
        })

        # Should NOT raise — the active timer satisfies the condition
        try:
            result = self.task.action_fsm_view_material()
            self.assertIsInstance(result, dict, "Expected an action dict returned")
        finally:
            timer.unlink()

    # ------------------------------------------------------------------
    # Test 3: Allow when timesheets exist (timer already stopped)
    # ------------------------------------------------------------------
    def test_allow_with_existing_timesheets(self):
        """No error raised when at least one timesheet is saved on the task."""
        self.fsm_project.require_start_to_sell = True

        # Create a timesheet entry manually (simulates Start→Stop completed)
        self.env['account.analytic.line'].create({
            'name': 'Work done',
            'task_id': self.task.id,
            'project_id': self.fsm_project.id,
            'unit_amount': 1.0,
            'employee_id': self.env['hr.employee'].search([
                ('company_id', '=', self.env.ref('base.main_company').id)
            ], limit=1).id,
        })

        result = self.task.action_fsm_view_material()
        self.assertIsInstance(result, dict, "Expected an action dict returned")

    # ------------------------------------------------------------------
    # Test 4: No block when project setting is disabled
    # ------------------------------------------------------------------
    def test_no_block_when_disabled(self):
        """No error raised when require_start_to_sell is False (default)."""
        self.fsm_project.require_start_to_sell = False

        result = self.task.action_fsm_view_material()
        self.assertIsInstance(result, dict, "Expected an action dict returned with setting disabled")
