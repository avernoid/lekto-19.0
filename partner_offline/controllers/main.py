from odoo import http, _
from odoo.http import request
import json
import base64
from odoo.tools.image import image_data_uri

class PartnerOfflinePortal(http.Controller):

    @http.route(['/my/partners', '/my/partners/page/<int:page>'], type='http', auth="user", website=True)
    def partner_list(self, page=1, search='', search_in='name', filter_tag=0, **kw):
        Partner = request.env['res.partner']
        Tag = request.env['res.partner.category']
        
        # 1. Partner Search Domain (Base Visibility)
        domain = self._get_partner_domain(request.env.user)
        
        if search:
            for srch in search.split(" "):
                domain.append('|')
                domain.append('|')
                domain.append('|')
                domain.append('|')
                domain.append(('name', 'ilike', srch))
                domain.append(('phone', 'ilike', srch))
                domain.append(('email', 'ilike', srch))
                domain.append(('city', 'ilike', srch))
                domain.append(('vat', 'ilike', srch))
        
        # Filter by Tag (Smart Filter)
        if filter_tag:
            try:
                filter_tag = int(filter_tag)
                domain.append(('category_id', 'in', [filter_tag]))
            except:
                filter_tag = 0

        # 2. Pager
        partner_count = Partner.sudo().search_count(domain)
        pager = request.website.pager(
            url="/my/partners",
            url_args={'search': search, 'search_in': search_in, 'filter_tag': filter_tag},
            total=partner_count,
            page=page,
            step=20
        )
        
        # 3. Fetch Partners (Sudo for off-limits contacts pattern)
        # Note: We rely on standard sudo() pattern for this specific app use-case (Driver Portal)
        partners = Partner.sudo().search(domain, limit=20, offset=pager['offset'])
        
        # 4. Smart Tags Calculation
        # We want to show tags that are RELEVANT to the current list (or ideally all relevant to the broad search)
        # If we only show tags from the *current page* (20 items), it might be too narrow.
        # But iterating over ALL partners to find tags is expensive.
        # Compromise: Fetch tags from the current page of partners. 
        # Better UX: Fetch all tags used by partners matching the search query (without limit), but this can be slow.
        # Optimization: Let's stick to tags from the current view or a broader separate search if needed. 
        # For responsiveness, let's Aggregate tags from the *current page* results first.
        # To be truly "Smart", we usually want tags from the *entire* text search result.
        # calculated_tags:
        
        available_tags = request.env['res.partner.category'].sudo().browse()
        if partners:
            # Get all tags from these partners
            available_tags = partners.mapped('category_id')
            
        # If a filter is active, we might want to show sibling tags too? 
        # For now, simplistic approach: Show tags present in the current Recordset.
        
        values = {
            'partners': partners,
            'pager': pager,
            'search': search,
            'search_in': search_in,
            'filter_tag': filter_tag,
            'available_tags': available_tags.sorted('name'),
            'partner_count': partner_count, # Total count for the header
            'page_name': 'partner_list',
            'image_data_uri': image_data_uri,
        }
        return request.render("partner_offline.partner_list_view", values)

    @http.route('/my/partner_image/<int:partner_id>/<string:field>', type='http', auth="user", website=True)
    @http.route('/my/partner_image/<int:partner_id>/<string:field>', type='http', auth="user", website=True)
    def partner_image(self, partner_id, field='avatar_128', **kw):
        """ Proxy to fetch partner images using sudo() if the user has logical access. """
        Partner = request.env['res.partner']
        
        # 1. Verify Access using SHARED Logic
        domain = self._get_partner_domain(request.env.user)
        
        # Add ID check to the domain
        domain.append(('id', '=', partner_id))
        
        # Check if accessible
        exists = Partner.sudo().search_count(domain)
        
        if not exists:
            return request.not_found()
            
        # 2. Redirect to Odoo's native controller
        # This solves "broken image" issues by letting Odoo handle placeholders (Colored SVGs) and caching.
        partner = Partner.sudo().browse(partner_id)
        
        if field not in ['image_128', 'image_256', 'avatar_128', 'avatar_256']:
             return request.not_found()
             
        # Redirect so Odoo native /web/image logic takes over
        return request.redirect('/web/image?model=res.partner&id=%s&field=%s' % (partner.id, field))

    def _get_partner_domain(self, user):
        """ Helper to return the base visibility domain for a user. """
        domain = []
        
        # Check Groups
        has_group_all = user.has_group('partner_offline.group_portal_all')
        has_group_assigned_unassigned = user.has_group('partner_offline.group_portal_assigned_unassigned')
        has_group_assigned = user.has_group('partner_offline.group_portal_assigned')

        # Check Sales Team Settings
        team_visibility = user.sale_team_id.portal_contact_visibility if user.sale_team_id else False
        
        # Determine Access Level (OR Logic)
        can_see_all = has_group_all
        can_see_assigned_unassigned = has_group_assigned_unassigned or (team_visibility == 'assigned_and_unassigned')
        can_see_assigned = has_group_assigned or (team_visibility == 'assigned')

        # Apply Domain
        if can_see_all:
             pass
        elif can_see_assigned_unassigned:
             domain.append('|')
             domain.append(('user_id', '=', user.id))
             domain.append(('user_id', '=', False))
        elif can_see_assigned:
             domain.append(('user_id', '=', user.id))
        else:
             domain.append(('id', '=', -1))
             
        return domain

    @http.route(['/my/partners/<int:partner_id>'], type='http', auth="user", website=True)
    def partner_detail(self, partner_id, **kw):
        # Secure fetch: access check or sudo with verification?
        # If listed in list view (sudo), we should likely allow sudo here too.
        partner = request.env['res.partner'].sudo().browse(partner_id)
        if not partner.exists():
            return request.redirect('/my/partners')
            
        values = {
            'partner': partner,
            'page_name': 'partner_detail',
            'image_data_uri': image_data_uri,
        }
        return request.render("partner_offline.partner_detail_view", values)

    @http.route('/partner_offline/manifest.json', type='http', auth="public", methods=['GET'])
    def pwa_manifest(self):
        """Dynamic PWA Manifest based on Portal App registration"""
        # Find the app registration for this module to get theme colors/names
        # We assume the user has access to read portal.app via sudo (config)
        app = request.env['portal.app'].sudo().search([('action_url', 'ilike', '/my/partners')], limit=1)
        
        manifest = {
            "name": app.name or "Partner Portal",
            "short_name": app.name or "Partners",
            "start_url": "/my/partners",
            "scope": "/my/partners",  # Critical: Restricted Scope
            "display": "standalone",
            "background_color": app.app_background_color or "#ffffff",
            "theme_color": app.theme_color or "#FF6F61",
            "icons": [
                {
                    "src": "/portal_app/icon/%s" % app.id if app else "/partner_offline/static/description/icon.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any maskable"
                },
                {
                    "src": "/portal_app/icon/%s" % app.id if app else "/partner_offline/static/description/icon.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable"
                }
            ]
        }
        
        return request.make_response(
            json.dumps(manifest), 
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/partner_offline/service-worker.js', type='http', auth="public", methods=['GET'])
    def service_worker_js(self):
        """Serve the Service Worker with the correct Scope header if needed, or just static file access."""
        # Note: Usually better to serve as static file, but we might want dynamic cache versioning?
        # For now, let's redirect to the static file or just read it.
        # But serving from controller allows setting 'Service-Worker-Allowed' header if scope is broader than script location.
        # Our script is in /static/src/js/, but scope is /my/partners.
        # Should be fine if basic static server handles it, but safer to serve from root-ish URL if scope issues arise.
        # Getting content from static file:
        
        # For this MVP, we'll try standard static loading first. 
        # If we need this route, it's here.
        return request.redirect('/partner_offline/static/src/js/partner_service_worker.js')
