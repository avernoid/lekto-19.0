from odoo import http
from odoo.http import request
import json

class PwaController(http.Controller):

    @http.route('/portal_app/manifest.webmanifest', type='http', auth='public', website=True)
    def manifest(self):
        """Generates the PWA manifest dynamically."""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        company = request.env.company
        
        manifest_data = {
            "name": "Portal App",
            "short_name": "Portal",
            "start_url": "/my/home", # Should redirect to launcher if user has group
            "display": "standalone",
            "background_color": "#667eea",
            "theme_color": "#667eea",
            "scope": "/",
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
        
        return request.make_response(
            json.dumps(manifest_data),
            headers=[('Content-Type', 'application/manifest+json')]
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
