from odoo import models, fields, api, _

class ProjectTaskEvidence(models.Model):
    _name = 'project.task.evidence'
    _description = 'Project Task Evidence'
    _order = 'sequence, id'

    name = fields.Char(
        string='Description', 
        required=False,
        help="Short description or label for this photo evidence."
    )
    sequence = fields.Integer(string='Sequence', default=10)
    image = fields.Image(
        string='Image', 
        max_width=1280, 
        max_height=1280, 
        required=True,
        help="Photo evidence captured. Automatically resized to max 1280x1280."
    )
    task_id = fields.Many2one(
        'project.task', 
        string='Task', 
        required=True, 
        ondelete='cascade',
        help="The Project Task this evidence belongs to."
    )
    product_id = fields.Many2one(
        'product.product', 
        string='Product',
        help="The Product associated with the evidence, usually inherited from the Task's Sales Order Item."
    )
    
    latitude = fields.Float(
        string='Latitude', 
        digits=(10, 7), 
        aggregator=None,
        help="GPS Latitude captured automatically from the device."
    )
    longitude = fields.Float(
        string='Longitude', 
        digits=(10, 7), 
        aggregator=None,
        help="GPS Longitude captured automatically from the device."
    )
    exclude_from_report = fields.Boolean(
        string="Exclude from Report",
        default=False,
        help="If checked, this photo will not appear in the customer-facing report."
    )
    
    map_url = fields.Char(
        string='Map Link', 
        compute='_compute_map_url',
        help="Direct link to view the location on Google Maps."
    )

    @api.depends('latitude', 'longitude')
    def _compute_map_url(self):
        for record in self:
            if record.latitude and record.longitude:
                record.map_url = f"https://www.google.com/maps/search/?api=1&query={record.latitude},{record.longitude}"
            else:
                record.map_url = False
