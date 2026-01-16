from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class AppLauncherPortal(CustomerPortal):

    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        # Check if user is in the "Portal App User" group
        if request.env.user.has_group('portal_app_launcher.group_portal_app_user'):
            # Fetch available apps for this user
            apps = request.env['portal.app'].sudo().search([])
            # Filter apps by group if necessary
            # We use sudo() on apps to allow reading the 'group_ids' field (which points to res.groups, usually restricted)
            # We compare with user.groups_id which the user can read about themselves
            visible_apps = apps.filtered(lambda a: not a.group_ids or (a.group_ids & request.env.user.groups_id))
            
            return request.render('portal_app_launcher.portal_app_launcher_home', {
                'apps': visible_apps,
                'user': request.env.user,
            })
        
        # Fallback to standard portal
        return super(AppLauncherPortal, self).home(**kw)
