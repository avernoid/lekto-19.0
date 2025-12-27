# -*- coding: utf-8 -*-
import math
from odoo import fields, models, api, _, exceptions
from odoo.exceptions import ValidationError

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    in_accuracy = fields.Float(string="In Accuracy (m)",
        help="GPS signal accuracy at Check-in (meters). Lower is better. If this exceeds limits, policy may block the action.")
    out_accuracy = fields.Float(string="Out Accuracy (m)",
        help="GPS signal accuracy at Check-out (meters). Lower is better. Used for location reliability audit.")

    location_reliability = fields.Selection([
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('unknown', 'Unknown'),
    ], string="Location Reliability", default='unknown',
        help="Trustworthiness of the reported coordinates based on GPS accuracy. High (<10m), Medium (<50m), or Low.")

    distance_meters = fields.Float(string="Distance (m)",
        help="Calculated distance between the employee's reported position and the center of the assigned work location.")

    location_status = fields.Selection([
        ('inside', 'Inside Expected Location'),
        ('outside', 'Outside Expected Location'),
        ('not_applicable', 'Not Applicable'),
    ], string="Location Status",
        help="Determines if the action was performed within the allowed radius. 'Not Applicable' means validation was disabled for this action.")

    in_out_of_location_reason = fields.Text(string="In Reason",
        help="Justification provided by the employee when marking check-in outside the permitted zone.")
    out_out_of_location_reason = fields.Text(string="Out Reason",
        help="Justification provided by the employee when marking check-out outside the permitted zone.")

    def _get_haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians 
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

        # haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a)) 
        r = 6371000 # Radius of earth in meters.
        return c * r

    def _get_effective_config(self, employee, company):
        """
        Resolve effective configuration: hr.job value OR company default value.
        """
        job = employee.job_id
        def get_val(field):
            if job and job[field]:
                return job[field]
            return company['%s_default' % field]

        return {
            'geo_enforced': get_val('attendance_geo_enforced'),
            'radius': get_val('attendance_radius_m'),
            'out_policy': get_val('out_of_location_policy'),
            'accuracy_policy': get_val('low_accuracy_policy'),
            'high_max': get_val('accuracy_high_max'),
            'medium_max': get_val('accuracy_medium_max'),
            'gps_unavailable_policy': get_val('gps_unavailable_policy'),
            'no_location_policy': get_val('no_location_policy'),
        }

    def _validate_geolocation(self, vals, mode='in'):
        """
        Main validation logic for geolocation control.
        """
        employee = self.env['hr.employee'].browse(vals.get('employee_id') or self.employee_id.id)
        if not employee:
            return {}

        # 1. Determine Expected Location
        today = fields.Date.context_today(self)
        weekday_idx = fields.Date.to_date(today).weekday()
        days_fields = [
            'monday_location_id', 'tuesday_location_id', 'wednesday_location_id',
            'thursday_location_id', 'friday_location_id', 'saturday_location_id',
            'sunday_location_id'
        ]
        weekday_field = days_fields[weekday_idx]
        
        expected_location = employee.exceptional_location_id or (weekday_field in employee._fields and employee[weekday_field]) or False
        
        company = employee.company_id
        config = self._get_effective_config(employee, company)

        if not expected_location:
            if config['no_location_policy'] == 'block':
                raise ValidationError(_("No work location assigned for today. Attendance blocked by policy."))
            return {'location_status': 'not_applicable'} if config['no_location_policy'] == 'allow_mark' else {}

        if not config['geo_enforced']:
            return {'location_status': 'not_applicable'}

        # 2. Capture and Evaluate Geolocation
        lat = vals.get('%s_latitude' % mode) or self['%s_latitude' % mode]
        lon = vals.get('%s_longitude' % mode) or self['%s_longitude' % mode]
        acc = vals.get('%s_accuracy' % mode) or self['%s_accuracy' % mode]

        # GPS Unavailable
        if not lat or not lon:
            policy = config['gps_unavailable_policy']
            if policy == 'block':
                raise ValidationError(_("GPS coordinates are required to mark attendance."))
            elif policy == 'allow_reason' and not vals.get('%s_out_of_location_reason' % mode):
                raise exceptions.UserError("GEO_REASON_REQUIRED")
            return {'location_status': 'outside', 'location_reliability': 'unknown'}

        # Reliability
        reliability = 'low'
        if acc <= config['high_max']:
            reliability = 'high'
        elif acc <= config['medium_max']:
            reliability = 'medium'

        # Accuracy Policy
        if reliability == 'low' and config['accuracy_policy'] == 'block':
            raise ValidationError(_("Location accuracy is too low (%s m). Attendance blocked.") % acc)

        # Distance
        distance = self._get_haversine_distance(lat, lon, expected_location.latitude, expected_location.longitude)
        status = 'inside' if distance <= config['radius'] else 'outside'

        # Out of Radio Policy
        if status == 'outside':
            policy = config['out_policy']
            if policy == 'block' and status == 'outside':
                raise ValidationError(_("You are outside the permitted area (Distance: %s m, Radio: %s m).") % (int(distance), config['radius']))
            elif policy == 'allow_reason' and status == 'outside' and not vals.get('%s_out_of_location_reason' % mode):
                raise exceptions.UserError("GEO_REASON_REQUIRED")
            # Note: allow_mark is handled by saving the data

        return {
            'location_reliability': reliability,
            'distance_meters': distance,
            'location_status': status,
            '%s_accuracy' % mode: acc,
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id') and vals.get('check_in') and not vals.get('check_out'):
                # Check-in validation
                geo_vals = self._validate_geolocation(vals, mode='in')
                vals.update(geo_vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'check_out' in vals and vals.get('check_out') and not any(self.mapped('check_out')):
            # Check-out validation (only for first check-out update)
            for attendance in self:
                geo_vals = attendance._validate_geolocation(vals, mode='out')
                # We can't update vals directly for multiple attendances if they differ, 
                # but standard Odoo flow is one attendance at a time for check-out.
                # If it's a batch write, it's rare for check-out.
                super(HrAttendance, attendance).write({**vals, **geo_vals})
            return True
        return super().write(vals)
