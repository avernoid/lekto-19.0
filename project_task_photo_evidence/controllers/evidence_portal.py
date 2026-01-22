from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64
from odoo import SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

class EvidencePortal(CustomerPortal):

    @http.route(['/my/evidence/tasks', '/my/evidence/tasks/page/<int:page>'], type='http', auth="user", website=True)
    def evidence_tasks(self, page=1, filter_by='pending', filter_tag=False, filter_product=False, filter_project=False, **kw):
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
            
        user = request.env.user
        
        # Base Domain: Assigned to user + Has Evidence Configured
        # Now using evidence_product_ids instead of sale_line_id
        base_domain = [
            ('user_ids', 'in', [user.id]),
            ('evidence_product_ids', '!=', False), 
        ]
        
        # 1. Find ALL Pending Tasks to compute available filters options (Requirement: "appear in 'To Do'")
        pending_domain = base_domain + [('state', 'not in', ['1_done', '1_canceled'])]
        pending_tasks = request.env['project.task'].sudo().search(pending_domain)
        
        # Extract unique Tags, Products AND Projects for the Filter UI
        available_tags = pending_tasks.mapped('tag_ids').sorted('name')
        available_products = pending_tasks.mapped('evidence_product_ids').sorted('name')
        available_projects = pending_tasks.mapped('project_id').sorted('name')
        
        # 2. Build Display Domain based on user selection
        display_domain = base_domain[:]
        
        if filter_by == 'done':
            # Show completed/canceled tasks
            display_domain.append(('state', 'in', ['1_done', '1_canceled']))
        else:
            # Show pending tasks (in progress, waiting, etc)
            filter_by = 'pending' # ensure valid value
            display_domain.append(('state', 'not in', ['1_done', '1_canceled']))
            
        try:
            if filter_tag:
                display_domain.append(('tag_ids', 'in', [int(filter_tag)]))
        except (ValueError, TypeError):
            filter_tag = False
            
        try:
            if filter_product:
                display_domain.append(('evidence_product_ids', 'in', [int(filter_product)]))
        except (ValueError, TypeError):
            filter_product = False

        try:
            if filter_project:
                display_domain.append(('project_id', '=', int(filter_project)))
        except (ValueError, TypeError):
             filter_project = False

        # Search Logic (Name, Project, Product, Tag)
        search = kw.get('search')
        if search:
            display_domain.append('|')
            display_domain.append('|')
            display_domain.append('|')
            display_domain.append(('name', 'ilike', search))
            display_domain.append(('project_id.name', 'ilike', search))
            display_domain.append(('tag_ids.name', 'ilike', search))
            display_domain.append(('evidence_product_ids.name', 'ilike', search))
            
        # Pagination
        Task = request.env['project.task'].sudo()
        task_count = Task.search_count(display_domain)
        # pager
        url = "/my/evidence/tasks"
        url_args = {'filter_by': filter_by}
        if filter_tag:
            url_args['filter_tag'] = filter_tag
        if filter_product:
            url_args['filter_product'] = filter_product
        if filter_project:
            url_args['filter_project'] = filter_project
        if search:
            url_args['search'] = search
            
        pager = request.website.pager(
            url=url,
            total=task_count,
            page=page,
            step=20,
            url_args=url_args,
        )
        
        tasks = Task.search(display_domain, limit=20, offset=pager['offset'])
        
        return request.render('project_task_photo_evidence.evidence_app_home', {
            'tasks': tasks,
            'pager': pager,
            'filter_by': filter_by,
            'current_tag': int(filter_tag) if filter_tag else False,
            'current_product': int(filter_product) if filter_product else False,
            'current_project': int(filter_project) if filter_project else False,
            'available_tags': available_tags,
            'available_products': available_products,
            'available_projects': available_projects,
        })

    @http.route(['/my/evidence/task/<int:task_id>/upload'], type='http', auth="user", website=True)
    def evidence_task_upload(self, task_id, **kw):
        # browse as sudo to read product fields, but check ownership manually
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists() or request.env.user.id not in task.user_ids.ids:
             return request.redirect('/my/evidence/tasks') # Simple security check

        return request.render('project_task_photo_evidence.evidence_app_task_upload', {
            'task': task,
        })

    @http.route(['/my/evidence/task/<int:task_id>/process_upload'], type='http', auth="user", website=True, methods=['POST'])
    def process_upload(self, task_id, **kw):
        try:
            # browse as sudo to read product fields, but check ownership manually
            task = request.env['project.task'].sudo().browse(task_id)
            if not task.exists() or request.env.user.id not in task.user_ids.ids:
                return request.redirect('/my/evidence/tasks')

            # Get data from form
            files = request.httprequest.files.getlist('evidence_file')
            latitude = kw.get('latitude')
            longitude = kw.get('longitude')
            description = kw.get('evidence_name')
            
            # Product Logic
            product_id = False
            try:
                if kw.get('product_id'):
                    product_id = int(kw.get('product_id'))
            except:
                pass
                
            # If product_id provided, ensure it's valid for this task
            if product_id and product_id not in task.evidence_product_ids.ids:
                 # Fallback or error? For now, fallback to first available or empty?
                 # Let's enforce it. If invalid, maybe don't set it?
                 product_id = False

            # If no product selected but task has only one, auto-select it?
            # The form should handle this, but safe to double check:
            if not product_id and len(task.evidence_product_ids) == 1:
                product_id = task.evidence_product_ids[0].id
            
            # Custom Validation: Max Quantity
            if product_id:
                product = request.env['product.product'].sudo().browse(product_id)
                if product.evidence_required and product.evidence_max_qty > 0:
                    # 1. Calculate Max Qty
                    max_qty = product.evidence_max_qty
                    if task.sale_line_id and task.sale_line_id.product_id == product:
                         # Multiplier logic
                         max_qty = int(product.evidence_max_qty * task.sale_line_id.product_uom_qty)
                    
                    # 2. Count current evidence
                    current_count = request.env['project.task.evidence'].sudo().search_count([
                        ('task_id', '=', task.id),
                        ('product_id', '=', product.id)
                    ])
                    
                    # 3. Check if upload would exceed limit
                    if current_count + len([f for f in files if f]) > max_qty:
                        return request.redirect(f'/my/evidence/task/{task_id}/upload?error=Maximum evidence quantity ({max_qty}) reached for {product.name}.')

            for file in files:
                if file:
                    # Create evidence record
                    request.env['project.task.evidence'].create({
                        'task_id': task.id,
                        'name': description or file.filename,
                        'image': base64.b64encode(file.read()), # Binary field expects base64
                        'latitude': latitude,
                        'longitude': longitude,
                        'product_id': product_id
                    })
            
            return request.redirect(f'/my/evidence/task/{task_id}/upload')
            
        except Exception as e:
            _logger.exception("Portal Upload Crash for Task %s", task_id)
            return request.redirect(f'/my/evidence/task/{task_id}/upload?error=System Error: {str(e)}. Full technical details have been logged to the Server Logs.')

    @http.route(['/my/evidence/task/<int:task_id>/complete'], type='http', auth="user", website=True, methods=['POST'])
    def complete_task(self, task_id, **kw):
        try:
            # ... existing code ...
            # browse as sudo to read product/project fields, but check ownership manually
            task = request.env['project.task'].sudo().browse(task_id)
            if not task.exists() or request.env.user.id not in task.user_ids.ids:
                return request.redirect('/my/evidence/tasks')
                
            project = task.project_id
            
            # Explicit Validation (Quality Gate)
            if project.force_min_photos:
                missing_items = task._get_missing_evidence_requirements()
                if missing_items:
                    # Pass code instead of raw HTML to allow Template to render rich list safely
                    return request.redirect(f'/my/evidence/task/{task_id}/upload?error=missing_evidence')

            vals = {}
            
            if project.evidence_final_stage_id:
                vals['stage_id'] = project.evidence_final_stage_id.id
                
            if project.evidence_final_state:
                vals['state'] = project.evidence_final_state
                
            if vals:
                 # FIX: Use SUPERUSER_ID to avoid "Portal User cannot read groups/users" during automation
                 task.with_user(SUPERUSER_ID).write(vals)
            
            return request.redirect('/my/evidence/tasks')
            
        except Exception as e:
             _logger.exception("Portal Complete Crash for Task %s", task_id)
             return request.redirect(f'/my/evidence/task/{task_id}/upload?error=System Error: {str(e)}. Full technical details have been logged to the Server Logs.')
