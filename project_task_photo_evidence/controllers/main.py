from odoo import http
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound

class ProjectTaskEvidenceController(http.Controller):

    @http.route('/project/task/evidence/<int:task_id>', type='http', auth='public', website=True)
    def task_evidence_report(self, task_id, access_token=None, **kwargs):
        """ Render the public evidence report if token is valid. """
        task = request.env['project.task'].sudo().browse(task_id)
        
        if not task.exists():
            raise NotFound()

        # Validate Access Token
        if not access_token or not task.access_token or access_token != task.access_token:
             # Odoo's _portal_ensure_token manages the token, but direct comparison is safest here 
             # given we are not using the full portal mixin controller logic but a custom lightweight one.
             raise Forbidden("Invalid access token.")

        # If valid, render the report template directly
        # We pass 'docs' as a list to match the report template iteration structure
        return request.render('project_task_photo_evidence.report_evidence_template', {
            'docs': task,
            'public_view': True,
        })

    @http.route('/project/evidence/<int:project_id>', type='http', auth='public', website=True)
    def project_evidence_report(self, project_id, access_token=None, **kwargs):
        """ Render the public evidence report for the entire project if token is valid. """
        project = request.env['project.project'].sudo().browse(project_id)
        
        if not project.exists():
            raise NotFound()

        if not access_token or not project.access_token or access_token != project.access_token:
             raise Forbidden("Invalid access token.")

        # Render project report
        return request.render('project_task_photo_evidence.report_project_evidence_template', {
            'docs': project,
            'public_view': True,
        })
