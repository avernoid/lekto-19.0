# -*- coding: utf-8 -*-
from odoo import fields, models

class WorkLocation(models.Model):
    _inherit = 'hr.work.location'

    latitude = fields.Float(string="Latitude", digits=(10, 7),
        help="Geographical latitude of the work location center point (e.g., -12.046374). Precision is vital for geofencing.")
    longitude = fields.Float(string="Longitude", digits=(10, 7),
        help="Geographical longitude of the work location center point (e.g., -77.042793). Ensure this matches the physical entrance.")
