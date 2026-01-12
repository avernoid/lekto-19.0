from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

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
    
    evidence_report_url = fields.Char(
        string='Evidence Report URL', 
        compute='_compute_evidence_report_url',
        help="Public link to share the Photo Evidence report."
    )
    
    evidence_warning_msg = fields.Html(
        string='Evidence Warning',
        compute='_compute_evidence_warning_msg'
    )

    @api.depends('evidence_ids', 'evidence_ids.exclude_from_report', 'sale_line_id.product_id.evidence_required', 'sale_line_id.product_id.evidence_min_qty')
    def _compute_evidence_warning_msg(self):
        for task in self:
            msg = False
            if task.sale_line_id and task.sale_line_id.product_id:
                product = task.sale_line_id.product_id
                if product.evidence_required and product.evidence_min_qty > 0:
                    # Count valid evidences for this specific product
                    valid_evidences = task.evidence_ids.filtered(lambda e: e.product_id == product and not e.exclude_from_report)
                    if len(valid_evidences) < product.evidence_min_qty:
                        msg = _(
                            '<div class="alert alert-warning" role="alert" style="margin-bottom: 10px;">'
                            '<strong>⚠️ Attention:</strong> This product requires a minimum of <b>%s</b> photos, '
                            'but only <b>%s</b> are currently valid (not excluded).'
                            '</div>'
                        ) % (product.evidence_min_qty, len(valid_evidences))
            task.evidence_warning_msg = msg

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
            # Check by product if applicable, or general limit?
            # Requirement says: "Control: ValidationError si se supera evidence_max_qty."
            # We assume this limit comes from the product associated with the task (via sale_line_id).
            if task.sale_line_id and task.sale_line_id.product_id:
                product = task.sale_line_id.product_id
                if product.evidence_required and product.evidence_max_qty > 0:
                    evidences = task.evidence_ids.filtered(lambda e: e.product_id == product)
                    if len(evidences) > product.evidence_max_qty:
                         raise ValidationError(_("You cannot add more than %s evidence(s) for product %s.") % (product.evidence_max_qty, product.name))
