from odoo import models, fields

class PortalApp(models.Model):
    _name = 'portal.app'
    _description = 'Portal Application'
    _order = 'sequence, id'

    name = fields.Char(
        string="Name", 
        required=True, 
        translate=True, 
        help="The display name of the application as seen by portal users."
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Determines the display order in the launcher. Lower numbers appear first."
    )
    image = fields.Image(
        string="Icon", 
        max_width=512, 
        max_height=512,
        help="The icon image for the app. Recommended size is 512x512px with a transparent background."
    )
    action_url = fields.Char(
        string="Action URL", 
        required=True, 
        help="The portal route or external URL where the app redirects users (e.g., '/my/evidence/tasks')."
    )
    group_ids = fields.Many2many(
        'res.groups', 
        string="Allowed Groups", 
        help="Grant access to specific user groups. If empty, the app is visible to all authorized portal users."
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        help="If unchecked, the app will be hidden from the launcher dashboard without being deleted."
    )
