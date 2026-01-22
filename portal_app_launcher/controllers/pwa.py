from odoo import http
from odoo.http import request
import json

class PwaController(http.Controller):

    @http.route('/portal_app/manifest.webmanifest', type='http', auth='public', website=True)
    def manifest(self, app_mode=None):
        """Generates the PWA manifest dynamically."""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        company = request.env.company
        
        # Default Manifest (Portal App)
        manifest_data = {
            "name": "Portal App",
            "short_name": "Portal",
            "start_url": "/my/home",
            "display": "standalone",
            "background_color": "#667eea",
            "theme_color": "#667eea",
            "scope": "/my/home", # Restrict scope to allow other apps
            "id": "/my/home",    # Unique ID for Portal App
            "icons": [
                {
                    "src": "/portal_app_launcher/static/description/icon.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "/portal_app_launcher/static/description/icon.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ]
        }

        # Override for Evidence App
        # Override based on App Technical Name
        if app_mode:
            # Sudo to read configuration (safe as it is just colors/names)
            app = request.env['portal.app'].sudo().search([('technical_name', '=', app_mode)], limit=1)
            if app:
                manifest_data.update({
                    "name": app.pwa_name or app.name,
                    "short_name": app.pwa_name or app.name,
                    "start_url": app.action_url,
                    # Dynamic Scope: Use the action_url base path or default to root
                    "scope": app.action_url if app.action_url.endswith('/') else f"{app.action_url}/", 
                    
                    "id": f"/my/{app.technical_name}/",    
                    "background_color": app.background_color,
                    "theme_color": app.theme_color,
                    "icons": [
                        {
                            "src": f"/portal_app/icon/{app.id}" if app.image else "/portal_app_launcher/static/description/icon.png",
                            "sizes": "192x192",
                            "type": "image/png",
                            "purpose": "any maskable"
                        },
                        {
                            "src": f"/portal_app/icon/{app.id}" if app.image else "/portal_app_launcher/static/description/icon.png",
                            "sizes": "512x512",
                            "type": "image/png",
                            "purpose": "any maskable"
                        }
                    ],
                    "orientation": "portrait",
                    "categories": ["business", "productivity"]
                })
        
        return request.make_response(
            json.dumps(manifest_data),
            headers=[('Content-Type', 'application/manifest+json')]
        )

    @http.route('/portal_app/icon/<int:app_id>', type='http', auth='public', website=True)
    def app_icon(self, app_id):
        """Serves the App Icon publicly (but securely via sudo) for PWA availability."""
        app = request.env['portal.app'].sudo().browse(app_id)
        if not app.exists() or not app.image:
             return request.not_found()
        
        import base64
        try:
             # Odoo Binary fields are usually base64 encoded
             image_data = base64.b64decode(app.image)
        except:
             image_data = app.image

        return request.make_response(
            image_data,
            headers=[('Content-Type', 'image/png')]
        )

    @http.route('/service-worker.js', type='http', auth='public', website=True)
    def service_worker(self):
        """Serves the Service Worker file from static with correct headers."""
        from odoo.modules import get_module_resource
        
        sw_path = get_module_resource(
            'portal_app_launcher', 'static/src/js', 'service-worker.js'
        )
        
        if not sw_path:
             return request.not_found()

        with open(sw_path, 'rb') as f:
            data = f.read()

        return request.make_response(
            data,
            headers=[
                ('Content-Type', 'application/javascript'),
                ('Service-Worker-Allowed', '/')
            ]
        )
