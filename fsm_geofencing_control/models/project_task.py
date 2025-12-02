from odoo import fields, models, api, _
from odoo.exceptions import UserError
from ..utils.geo_utils import calculate_distance


class ProjectTask(models.Model):
    _inherit = "project.task"

    last_latitude = fields.Float(
        string="Last Latitude",
        digits=(10, 7),
        help="Last recorded latitude when timer was started or stopped."
    )
    
    last_longitude = fields.Float(
        string="Last Longitude",
        digits=(10, 7),
        help="Last recorded longitude when timer was started or stopped."
    )

    def action_timer_start(self):
        """
        Override to add distance validation before starting timer.
        Validates technician location if control_distance_on_start is enabled.
        """
        for task in self:
            if not task.is_fsm:
                continue
                
            # Check if distance control is enabled
            if task.project_id.control_distance_on_start and task.project_id.allow_geolocation:
                geolocation = self.env.context.get("geolocation")
                
                if not geolocation or not geolocation.get("success"):
                    raise UserError(_(
                        "Cannot start timer: Unable to get your current location. "
                        "Please enable location services and try again."
                    ))
                
                # Get technician coordinates
                tech_latitude = geolocation.get("latitude")
                tech_longitude = geolocation.get("longitude")
                
                # Get customer coordinates
                customer = task.partner_id
                customer_latitude = customer.partner_latitude
                customer_longitude = customer.partner_longitude
                
                # Validate customer has geolocation
                if not customer_latitude or not customer_longitude:
                    raise UserError(_(
                        "Cannot start timer: Customer '%(customer)s' does not have a valid geolocation. "
                        "Please set the customer's address and geolocate it before starting the timer.",
                        customer=customer.name
                    ))
                
                # Calculate distance
                distance = calculate_distance(
                    tech_latitude, tech_longitude,
                    customer_latitude, customer_longitude
                )
                
                # Validate distance
                allowed_distance = task.project_id.allowed_distance
                if distance > allowed_distance:
                    raise UserError(_(
                        "Cannot start timer: You are too far from the customer location.\n\n"
                        "Your distance: %(distance)s m\n"
                        "Maximum allowed: %(allowed)s m\n\n"
                        "Please move closer to the customer location and try again.",
                        distance=round(distance, 2),
                        allowed=allowed_distance
                    ))
            
            # Store last known location if geolocation is available
            if task.project_id.allow_geolocation:
                geolocation = self.env.context.get("geolocation")
                if geolocation and geolocation.get("success"):
                    task.write({
                        'last_latitude': geolocation.get("latitude"),
                        'last_longitude': geolocation.get("longitude"),
                    })
        
        return super(ProjectTask, self).action_timer_start()

    def validate_distance_for_stop(self, geolocation):
        """
        Validate technician distance from customer when stopping timer.
        Called from the wizard before saving timesheet.
        
        Args:
            geolocation (dict): Geolocation data with latitude and longitude
            
        Raises:
            UserError: If validation fails
        """
        self.ensure_one()
        
        if not self.is_fsm:
            return
            
        # Check if distance control is enabled
        if not self.project_id.control_distance_on_stop or not self.project_id.allow_geolocation:
            return
        
        if not geolocation or not geolocation.get("success"):
            raise UserError(_(
                "Cannot stop timer: Unable to get your current location. "
                "Please enable location services and try again."
            ))
        
        # Get technician coordinates
        tech_latitude = geolocation.get("latitude")
        tech_longitude = geolocation.get("longitude")
        
        # Get customer coordinates
        customer = self.partner_id
        customer_latitude = customer.partner_latitude
        customer_longitude = customer.partner_longitude
        
        # Validate customer has geolocation
        if not customer_latitude or not customer_longitude:
            raise UserError(_(
                "Cannot stop timer: Customer '%(customer)s' does not have a valid geolocation. "
                "Please set the customer's address and geolocate it before stopping the timer.",
                customer=customer.name
            ))
        
        # Calculate distance
        distance = calculate_distance(
            tech_latitude, tech_longitude,
            customer_latitude, customer_longitude
        )
        
        # Validate distance
        allowed_distance = self.project_id.allowed_distance
        if distance > allowed_distance:
            raise UserError(_(
                "Cannot stop timer: You are too far from the customer location.\n\n"
                "Your distance: %(distance)s m\n"
                "Maximum allowed: %(allowed)s m\n\n"
                "Please move closer to the customer location and try again.",
                distance=round(distance, 2),
                allowed=allowed_distance
            ))
