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
            
            # DIRECT SQL: The most robust way to check groups if ORM is restricted/broken in this context.
            # This bypasses 'res.users' attribute access and 'res.groups' ACLs entirely.
            request.env.cr.execute("SELECT gid FROM res_groups_users_rel WHERE uid = %s", (request.env.user.id,))
            user_group_ids = [row[0] for row in request.env.cr.fetchall()]
            
            # Filter apps
            visible_apps = apps.filtered(lambda a: not a.group_ids or any(g.id in user_group_ids for g in a.group_ids))
            
            return request.render('portal_app_launcher.portal_app_launcher_home', {
                'apps': visible_apps,
                'user': request.env.user,
            })
        
        # Fallback to standard portal
        return super(AppLauncherPortal, self).home(**kw)
