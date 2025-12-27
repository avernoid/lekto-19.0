# -*- coding: utf-8 -*-
from odoo import fields, models

class HrJob(models.Model):
    _inherit = 'hr.job'

    attendance_geo_enforced = fields.Boolean(string="Attendance Geo-Enforced",
        help="If enabled, Odoo will validate the employee's GPS coordinates against their work location's coordinates during attendance actions. Disable this to skip validation for this specific job position.")
    
    attendance_radius_m = fields.Integer(string="Attendance Radius (m)",
        help="The maximum allowed distance (in meters) between the employee and the assigned work location. If an employee exceeds this radius, the system applies the 'Out of Location Policy'.")
    
    out_of_location_policy = fields.Selection([
        ('block', 'Block'),
        ('allow_reason', 'Allow with Reason'),
        ('allow_mark', 'Allow and Mark'),
    ], string="Out of Location Policy",
        help="Determines what happens when an employee checks in/out outside the allowed radius. 'Block' prevents the action; 'Allow with Reason' requires a mandatory justification; 'Allow and Mark' lets them proceed but flags the record for audit.")

    low_accuracy_policy = fields.Selection([
        ('block', 'Block'),
        ('warn', 'Allow with Warning'),
        ('allow', 'Allow'),
    ], string="Low Accuracy Policy",
        help="Action to take when the GPS signal is too weak. 'Block' prevents actions with poor signals; 'Allow with Warning' notifies the user; 'Allow' ignores signal quality.")

    accuracy_high_max = fields.Integer(string="High Accuracy Max (m)",
        help="Maximum margin of error (in meters) for a GPS signal to be considered 'High' reliability. Usually, 0-10m is ideal.")
    accuracy_medium_max = fields.Integer(string="Medium Accuracy Max (m)",
        help="Maximum margin of error (in meters) for a GPS signal to be considered 'Medium' reliability. Signals beyond this value are marked as 'Low' reliability.")

    gps_unavailable_policy = fields.Selection([
        ('block', 'Block'),
        ('allow_reason', 'Allow with Reason'),
        ('allow_mark', 'Allow and Mark'),
    ], string="GPS Unavailable Policy",
        help="System behavior when GPS coordinates cannot be retrieved (e.g., GPS disabled). 'Block' makes GPS mandatory for attendance.")

    no_location_policy = fields.Selection([
        ('no_validate', 'Do Not Validate'),
        ('allow_mark', 'Allow and Mark'),
        ('block', 'Block'),
    ], string="No Location Policy",
        help="Behavior when an employee signs in on a day without an assigned Work Location. 'Block' forces managers to assign locations before employees can work.")
