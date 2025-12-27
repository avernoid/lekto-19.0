# -*- coding: utf-8 -*-
from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    attendance_geo_enforced_default = fields.Boolean(string="Default Attendance Geo-Enforced",
        help="Fallback setting to enable validation if not specified on the Work Location.")
    attendance_radius_m_default = fields.Integer(string="Default Attendance Radius (m)", default=100,
        help="Fallback radius in meters if not specified on the Work Location.")
    
    out_of_location_policy_default = fields.Selection([
        ('block', 'Block'),
        ('allow_reason', 'Allow with Reason'),
        ('allow_mark', 'Allow and Mark'),
    ], string="Default Out of Location Policy", default='allow_mark',
        help="Global default policy for out-of-radius attendance actions.")

    low_accuracy_policy_default = fields.Selection([
        ('block', 'Block'),
        ('warn', 'Allow with Warning'),
        ('allow', 'Allow'),
    ], string="Default Low Accuracy Policy", default='allow',
        help="Global default policy for handling poor GPS signal quality.")

    accuracy_high_max_default = fields.Integer(string="Default High Accuracy Max (m)", default=10,
        help="Global threshold for 'High' reliability signal classification.")
    accuracy_medium_max_default = fields.Integer(string="Default Medium Accuracy Max (m)", default=50,
        help="Global threshold for 'Medium' reliability signal classification.")

    gps_unavailable_policy_default = fields.Selection([
        ('block', 'Block'),
        ('allow_reason', 'Allow with Reason'),
        ('allow_mark', 'Allow and Mark'),
    ], string="Default GPS Unavailable Policy", default='allow_mark',
        help="Global default policy for when coordinates cannot be retrieved.")

    no_location_policy_default = fields.Selection([
        ('no_validate', 'Do Not Validate'),
        ('allow_mark', 'Allow and Mark'),
        ('block', 'Block'),
    ], string="Default No Location Policy", default='no_validate',
        help="Global default behavior when no work location is assigned to the employee for the day.")
