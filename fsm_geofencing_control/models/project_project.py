from odoo import fields, models, api


class ProjectProject(models.Model):
    _inherit = "project.project"

    # TODO: COMPATIBILITY WARNING
    # In Odoo 19.0, 'allow_geolocation' is introduced by 'industry_fsm'.
    # When migrating to 19.0, DELETE this field definition to avoid conflict/duplication.
    # We use the same name now to ensure the database column is preserved ("Adopt and Drop" strategy).
    allow_geolocation = fields.Boolean(
        string="Allow Geolocation",
        default=False,
        help="Enable geolocation tracking for FSM tasks."
    )

    control_distance_on_start = fields.Boolean(
        string="Control Distance on Start",
        default=False,
        help="Validate technician is within allowed distance from customer when starting timer."
    )
    
    allowed_distance = fields.Float(
        string="Allowed Distance (m)",
        default=100.0,
        help="Maximum distance in meters allowed between technician and customer location."
    )
    
    control_distance_on_stop = fields.Boolean(
        string="Control Distance on Stop",
        default=False,
        help="Validate technician is within allowed distance from customer when stopping timer."
    )
    
    auto_mark_done = fields.Boolean(
        string="Auto Mark Done",
        default=False,
        help="Automatically mark task as done when logging time."
    )
    
    use_lost_reason = fields.Boolean(
        string="Require Lost Reason",
        default=False,
        help="Require lost reason when stopping timer without a confirmed sale order."
    )

    @api.onchange('allow_geolocation')
    def _onchange_allow_geolocation(self):
        """Reset distance control fields when geolocation is disabled."""
        if not self.allow_geolocation:
            self.control_distance_on_start = False
            self.control_distance_on_stop = False
