from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProjectTaskEvidenceWizard(models.TransientModel):
    _name = 'project.task.evidence.wizard'
    _description = 'Add Evidence Wizard'

    task_id = fields.Many2one('project.task', string='Task', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(
        string='Description', 
        required=False,
        help="Enter a brief description for this photo."
    )
    image = fields.Image(
        string='Image', 
        max_width=1280, 
        max_height=1280, 
        required=True,
        help="Upload the photo evidence here."
    )
    latitude = fields.Float(
        string='Latitude', 
        digits=(10, 7),
        help="Detected GPS Latitude."
    )
    longitude = fields.Float(
        string='Longitude', 
        digits=(10, 7),
        help="Detected GPS Longitude."
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_id'):
            task = self.env['project.task'].browse(self.env.context.get('active_id'))
            res['task_id'] = task.id
            if task.sale_line_id:
                res['product_id'] = task.sale_line_id.product_id.id
        return res

    def action_save(self):
        self.ensure_one()
        self._create_evidence()
        return {'type': 'ir.actions.act_window_close'}
    
    def action_save_and_new(self):
        self.ensure_one()
        self._create_evidence()
        # Re-open the wizard with clean fields, keeping task and product
        ctx = dict(self.env.context)
        ctx.update({
            'default_task_id': self.task_id.id,
            'default_product_id': self.product_id.id,
            'active_id': self.task_id.id,
            'active_model': 'project.task',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Photo Evidence'),
            'res_model': 'project.task.evidence.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx
        }

    def _create_evidence(self):
        # Validate Max Quantity before creating
        if self.product_id and self.product_id.evidence_required and self.product_id.evidence_max_qty > 0:
             current_evidence_count = self.env['project.task.evidence'].search_count([
                 ('task_id', '=', self.task_id.id),
                 ('product_id', '=', self.product_id.id)
             ])
             if current_evidence_count >= self.product_id.evidence_max_qty:
                 raise ValidationError(_("Maximum evidence quantity reached for this product."))

        self.env['project.task.evidence'].create({
            'task_id': self.task_id.id,
            'product_id': self.product_id.id,
            'name': self.name,
            'image': self.image,
            'latitude': self.latitude,
            'longitude': self.longitude,
        })
