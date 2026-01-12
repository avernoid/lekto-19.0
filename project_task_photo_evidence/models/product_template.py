from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    evidence_required = fields.Boolean(
        string="Evidence Required",
        help="If checked, tasks linked to this product (via Sales Order Item) will require photo evidence. "
             "This enforces quality control for field service operations."
    )
    evidence_min_qty = fields.Integer(
        string="Minimum Evidence", 
        default=0,
        help="Minimum number of photos required to consider the evidence collection sufficient for this product."
    )
    evidence_max_qty = fields.Integer(
        string="Maximum Evidence", 
        default=0,
        help="Maximum number of photos allowed for this product. Useful to prevent storage waste. "
             "Set to 0 for unlimited."
    )

    @api.constrains('evidence_min_qty', 'evidence_max_qty')
    def _check_evidence_qty(self):
        for record in self:
            if record.evidence_required:
                if record.evidence_max_qty > 0 and record.evidence_min_qty > record.evidence_max_qty:
                    raise ValidationError(_("Minimum evidence quantity cannot be greater than maximum evidence quantity."))
