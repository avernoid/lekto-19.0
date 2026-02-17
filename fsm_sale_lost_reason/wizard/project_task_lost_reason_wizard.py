from odoo import fields, models

class ProjectTaskLostReasonWizard(models.TransientModel):
    _name = 'project.task.lost.reason.wizard'
    _description = 'Task Lost Reason Wizard'

    task_id = fields.Many2one('project.task', string='Task', required=True)
    lost_reason_id = fields.Many2one('sale.lost.reason', string='Lost Reason', required=True)
    from_geo_visit = fields.Boolean(string='From Geo Visit')

    def action_confirm(self):
        self.ensure_one()
        self.task_id.write({'lost_reason_id': self.lost_reason_id.id})
        
        # If triggered from geolocation visit, we just mark as done to preserve that flow's behavior
        if self.from_geo_visit:
            self.task_id.write({'state': '1_done'})
            return {'type': 'ir.actions.act_window_close'}

        # Otherwise, standard FSM validate
        return self.task_id.with_context(self.env.context).action_fsm_validate()
