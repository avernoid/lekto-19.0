from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HrTimesheetStopTimerConfirmationWizard(models.Model):
    _inherit = 'hr.timesheet.stop.timer.confirmation.wizard'

    lost_reason_id = fields.Many2one(
        'sale.lost.reason',
        string='Lost Reason',
        help="Reason why the sale was not confirmed for this task."
    )
    
    control_distance_on_stop = fields.Boolean(
        related="timesheet_id.project_id.control_distance_on_stop",
        readonly=True
    )
    
    use_lost_reason = fields.Boolean(
        related="timesheet_id.project_id.use_lost_reason",
        readonly=True
    )
    
    auto_mark_done = fields.Boolean(
        related="timesheet_id.project_id.auto_mark_done",
        readonly=True
    )
    
    task_has_confirmed_sale = fields.Boolean(
        string="Task Has Confirmed Sale",
        compute="_compute_task_has_confirmed_sale",
        store=False
    )

    @api.depends('timesheet_id.task_id', 'timesheet_id.task_id.sale_order_id')
    def _compute_task_has_confirmed_sale(self):
        """Check if the task has a confirmed sale order."""
        for wizard in self:
            task = wizard.timesheet_id.task_id
            has_confirmed_sale = False
            
            if task and task.sale_order_id and task.sale_order_id.state in ['sale', 'done']:
                has_confirmed_sale = True
            else:
                # Also check for any sale orders linked to this task
                sale_orders = self.env['sale.order'].search([
                    ('task_id', '=', task.id),
                    ('state', 'in', ['sale', 'done'])
                ], limit=1)
                if sale_orders:
                    has_confirmed_sale = True
            
            wizard.task_has_confirmed_sale = has_confirmed_sale

    def action_save_timesheet(self):
        """
        Override to add distance validation and lost reason requirement.
        Also handles auto-marking task as done.
        """
        self.ensure_one()
        
        task = self.timesheet_id.task_id
        project = self.timesheet_id.project_id
        
        # Validate distance if control is enabled
        if task and task.is_fsm and self.control_distance_on_stop:
            geolocation = self.env.context.get("geolocation")
            task.validate_distance_for_stop(geolocation)
            
            # Store last known location
            if geolocation and geolocation.get("success"):
                task.write({
                    'last_latitude': geolocation.get("latitude"),
                    'last_longitude': geolocation.get("longitude"),
                })
        
        # Validate lost reason requirement
        if task and task.is_fsm and self.use_lost_reason:
            if not self.task_has_confirmed_sale and not self.lost_reason_id:
                raise ValidationError(_(
                    "Lost Reason is required when stopping timer without a confirmed sale order. "
                    "Please select a reason why the sale was not confirmed."
                ))
            
            # Save lost reason to task if provided
            if self.lost_reason_id and not self.task_has_confirmed_sale:
                task.write({'lost_reason_id': self.lost_reason_id.id})
        
        # Get auto_mark_done value before calling super
        auto_mark_done = project.auto_mark_done if project else False
        
        # Call super to save timesheet
        result = super(HrTimesheetStopTimerConfirmationWizard, self).action_save_timesheet()
        
        # Auto-mark task as done if enabled
        _logger.info(f"Auto-mark check: task={task}, is_fsm={task.is_fsm if task else None}, auto_mark_done={auto_mark_done}, project={project}")
        if task and task.is_fsm and auto_mark_done:
            _logger.info(f"Auto-marking task {task.id} as done")
            task.write({'fsm_done': True, 'state': '1_done'})
            _logger.info(f"Task {task.id} marked as done. State: {task.state}, fsm_done: {task.fsm_done}")
        else:
            _logger.info(f"Auto-mark skipped. Reasons: task={bool(task)}, is_fsm={task.is_fsm if task else False}, auto_mark_done={auto_mark_done}")
        
        return result
