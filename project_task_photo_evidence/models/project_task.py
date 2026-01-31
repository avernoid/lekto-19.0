from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import uuid

class ProjectTask(models.Model):
    _inherit = 'project.task'

    evidence_ids = fields.One2many(
        'project.task.evidence', 
        'task_id', 
        string='Evidence',
        help="List of photo evidence collected for this task."
    )
    
    sale_product_id = fields.Many2one(
        'product.product',
        related='sale_line_id.product_id',
        string='Sale Product',
        readonly=True
    )

    evidence_product_ids = fields.Many2many(
        'product.product',
        string='Evidence Products',
        compute='_compute_evidence_product_ids',
        store=True,
        readonly=False, # Allow manual editing
        domain="[('evidence_required', '=', True)]",
        help="Products that require photo evidence for this task."
    )
    
    @api.depends('sale_line_id', 'sale_line_id.product_id')
    def _compute_evidence_product_ids(self):
        for task in self:
            # If a sale line exists and has a product requiring evidence, add it.
            # We use a set to avoid duplicates and allow manual additions to persist if possible,
            # but standard Odoo compute+store behavior might reset manual changes if dependencies trigger.
            # Ideally, we want to ADD to the existing list, not replace it entirely, unless it's empty.
            if task.sale_line_id and task.sale_line_id.product_id:
                new_product = task.sale_line_id.product_id
                if new_product.evidence_required:
                    # Use Command.link (4) to add without clearing others (though compute usually replaces)
                    # To truly support "Manual + Auto", we often check if the value is already set.
                    # Simplified logic: If the computed product is not in the list, add it.
                    if new_product.id not in task.evidence_product_ids.ids:
                         task.write({'evidence_product_ids': [(4, new_product.id)]})
            
            # Since this is a compute method, we must assign something if it's not set, or ensuring it runs.
            # However, for manual editing + auto-sync, an onchange or write override is often better.
            # But let's stick to the requested "compute stored" but modify it to be additive if possible
            # or simply assign.
            # "standard" compute approach:
            # task.evidence_product_ids = [product] if product else []
            # But that kills manual entries.
            # Let's try to just Ensure the sale product is there.
            pass # We use the automation via write/onchange logic pattern or just let the field act largely manual with an onchange
            
    # BETTER APPROACH for "Manual + Sync": 
    # Use an Onchange or just override create/write.
    # But since I declared it as compute stored, I must implement it.
    # To avoid overwriting manual data, I will act only when sale_line_id changes (which triggers this).

    
    evidence_report_url = fields.Char(
        string='Evidence Report URL', 
        compute='_compute_evidence_report_url',
        help="Public link to share the Photo Evidence report."
    )
    
    evidence_warning_msg = fields.Html(
        string='Evidence Warning',
        compute='_compute_evidence_warning_msg'
    )

    @api.depends('evidence_ids', 'evidence_ids.exclude_from_report', 'evidence_product_ids', 'evidence_product_ids.evidence_required', 'evidence_product_ids.evidence_min_qty', 'sale_line_id.product_uom_qty')
    def _get_missing_evidence_requirements(self):
        """Returns a list of dicts describing missing evidence."""
        self.ensure_one()
        missing = []
        # Check requirements for ALL configured evidence products
        # FIX: access 'evidence_product_ids' via sudo() as Portal Users may not have read access to products
        # but validation logic needs to check them.
        for product in self.sudo().evidence_product_ids:
            if product.evidence_required and product.evidence_min_qty > 0:
                # Determine required quantity (Multiplier logic)
                required_qty = product.evidence_min_qty
                if self.sale_line_id and self.sale_line_id.product_id == product:
                        # Scale by SOL quantity
                        required_qty = int(product.evidence_min_qty * self.sale_line_id.product_uom_qty)
                
                # Count valid evidences for this specific product
                # We filter 'evidence_ids' on 'self' (the user's view of the task) to ensure they own the evidence
                # No need for sudo() on evidence_ids if the user created them.
                # FIX: Use sudo() to avoid AccessErrors if the portal user has restricted access to the field or model
                # Validation should check existential evidence, not just visible evidence.
                valid_evidences = self.sudo().evidence_ids.filtered(lambda e: e.product_id == product and not e.exclude_from_report)
                if len(valid_evidences) < required_qty:
                    missing.append({
                        'product_name': product.name,
                        'required': required_qty,
                        'current': len(valid_evidences)
                    })
        return missing

    @api.depends('evidence_ids', 'evidence_ids.exclude_from_report', 'evidence_product_ids', 'evidence_product_ids.evidence_required', 'evidence_product_ids.evidence_min_qty', 'sale_line_id.product_uom_qty')
    def _compute_evidence_warning_msg(self):
        for task in self:
            missing_items = task._get_missing_evidence_requirements()
            if missing_items:
                warnings = []
                for item in missing_items:
                    warnings.append(_(
                        '<li><b>%s</b>: Requires %s photos (Current: %s)</li>'
                    ) % (item['product_name'], item['required'], item['current']))
                
                msg = _('<div class="alert alert-warning" role="alert" style="margin-bottom: 10px;">'
                        '<strong>⚠️ Evidence Missing:</strong><ul>%s</ul></div>') % "".join(warnings)
                task.evidence_warning_msg = msg
            else:
                task.evidence_warning_msg = False

    @api.depends('access_token')
    def _compute_evidence_report_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for task in self:
            if task.access_token:
                task.evidence_report_url = f"{base_url}/project/task/evidence/{task.id}?access_token={task.access_token}"
            else:
                task.evidence_report_url = False

    def action_generate_evidence_token(self):
        for task in self:
            if not task.access_token:
                task.access_token = self.env['ir.config_parameter'].sudo()._get_param('database.uuid') # Just initialization, _portal_ensure_token does better
                task._portal_ensure_token()
        return True

    def action_revoke_evidence_token(self):
        self.sudo().write({'access_token': False})
        return True

    @api.constrains('evidence_ids')
    def _check_evidence_max_qty(self):
        for task in self:
            # Check for each product in evidence_product_ids or in the evidences themselves
            # We iterate over unique products present in the uploaded evidence
            products_in_evidence = task.evidence_ids.mapped('product_id')
            
            for product in products_in_evidence:
                if product.evidence_required and product.evidence_max_qty > 0:
                     # Determine max quantity (Multiplier logic)
                     max_qty = product.evidence_max_qty
                     if task.sale_line_id and task.sale_line_id.product_id == product:
                         max_qty = int(product.evidence_max_qty * task.sale_line_id.product_uom_qty)

                     evidences = task.evidence_ids.filtered(lambda e: e.product_id == product)
                     if len(evidences) > max_qty:
                         raise ValidationError(_("You cannot add more than %s evidence(s) for product %s.") % (max_qty, product.name))

    # --- Website Report Public Access ---
    website_access_token = fields.Char('Website Access Token', copy=False)
    
    website_report_url = fields.Char(
        string='Website Report URL', 
        compute='_compute_website_report_url',
        help="Public link to share the modern Website Evidence report."
    )

    @api.depends('website_access_token')
    def _compute_website_report_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for task in self:
            if task.website_access_token:
                task.website_report_url = f"{base_url}/project/website/evidence/{task.id}?access_token={task.website_access_token}"
            else:
                task.website_report_url = False

    def action_generate_website_token(self):
        for task in self:
            if not task.website_access_token:
                task.website_access_token = str(uuid.uuid4())
        return True

    def action_revoke_website_token(self):
        self.sudo().write({'website_access_token': False})
        return True

