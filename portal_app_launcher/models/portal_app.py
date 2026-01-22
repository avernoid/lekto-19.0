from odoo import models, fields, api, _

class PortalApp(models.Model):
    _name = 'portal.app'
    _description = 'Portal Application'
    _order = 'sequence, id'

    @api.constrains('technical_name')
    def _check_technical_name_uniq(self):
        for app in self:
            if app.technical_name and self.search_count([('technical_name', '=', app.technical_name), ('id', '!=', app.id)]) > 0:
                raise models.ValidationError(_("The technical name must be unique!"))

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
    
    # PWA Configuration
    technical_name = fields.Char(
        string="Technical Name",
        help="Internal identifier used by the PWA controller (e.g. 'evidence'). Must be unique."
    )
    pwa_name = fields.Char(
        string="PWA Display Name",
        help="Name displayed on the splash screen and home screen (if different from the App Name)."
    )

    color_scheme = fields.Selection(
        [
            ('light', 'Light (Clean)'),
            ('ocean', 'Ocean (Blue)'),
            ('sunset', 'Sunset (Orange)'),
            ('purple', 'Royalty (Purple)'),
            ('dark', 'Dark Mode'),
        ],
        string="Color Theme",
        default='light',
        required=True,
        help="Select a color theme to automatically configure the application's appearance."
    )

    theme_color = fields.Char(
        string="Theme Color",
        compute="_compute_colors",
        store=True,
        help="Hex color for the browser toolbar and status bar."
    )
    background_color = fields.Char(
        string="Splash Background",
        compute="_compute_colors",
        store=True,
        help="Hex color for the PWA splash screen."
    )
    app_background_color = fields.Char(
        string="App Background Color",
        compute="_compute_colors",
        store=True,
        help="Hex color for the application body background."
    )
    app_text_color = fields.Char(
        string="App Text Color",
        compute="_compute_colors",
        store=True,
        help="Hex color for the application text."
    )

    @api.depends('color_scheme')
    def _compute_colors(self):
        for app in self:
            if app.color_scheme == 'ocean':
                app.theme_color = "#007BFF"      # Bright Blue
                app.background_color = "#E3F2FD" # Very Light Blue (Splash)
                app.app_background_color = "#F0F8FF" # AliceBlue (Body)
                app.app_text_color = "#002a4d"   # Dark Blue Text
            elif app.color_scheme == 'sunset':
                app.theme_color = "#FF6B6B"      # Soft Red/Pink
                app.background_color = "#FFF5F5" # Very Light Red (Splash)
                app.app_background_color = "#FFFAFA" # Snow (Body)
                app.app_text_color = "#4a0f0f"   # Dark Red Text
            elif app.color_scheme == 'purple':
                app.theme_color = "#6F42C1"      # Purple
                app.background_color = "#F3E5F5" # Very Light Purple
                app.app_background_color = "#FAF5FF" # (Body)
                app.app_text_color = "#2a0a4a"   # Dark Purple Text
            elif app.color_scheme == 'dark':
                app.theme_color = "#1F1F1F"      # Dark Grey
                app.background_color = "#121212" # Almost Black
                app.app_background_color = "#121212" # Almost Black
                app.app_text_color = "#F8F9FA"   # Off-White
            else: # Light (Default)
                app.theme_color = "#FFFFFF"      # White Header
                app.background_color = "#FFFFFF" # White Splash
                app.app_background_color = "#F8F9FA" # Light Grey Body
                app.app_text_color = "#212529"   # Dark Grey Text
    

