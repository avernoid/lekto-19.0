from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class PleUpdatePurchaseTagsWizard(models.TransientModel):
    _name = 'ple.update.purchase.tags.wizard'
    _description = 'Wizard to Manual Update PLE Purchase Tags'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    config_ids = fields.Many2many('ple.purchase.tax.config', string='Configurations to Apply', required=True)

    def action_execute(self):
        self.ensure_one()
        _logger.info("PLE WIZARD: Starting Manual Tag Update for Company %s", self.company_id.name)
        
        success_count = 0
        error_count = 0
        logs = []

        # Force active_test=False to find all taxes
        AccountTax = self.env['account.tax'].sudo().with_context(active_test=False)
        
        for config in self.config_ids:
            # Construct XML ID: e.g. account.1_igv_18_dua
            # Note: ple_purchase_tax_config logic: prefix.company_id_suffix
            xml_id = "%s.%s_%s" % (config.tax_xml_prefix, self.company_id.id, config.tax_xml_suffix)
            
            tax = self.env.ref(xml_id, raise_if_not_found=False)
            
            if not tax:
                msg = "Tax NOT FOUND for XML ID: %s" % xml_id
                _logger.warning("PLE WIZARD: %s", msg)
                logs.append(msg)
                error_count += 1
                continue

            # Update Repartition Lines
            lines_to_update = self.env['account.tax.repartition.line']
            
            if config.repartition_type == 'base':
                lines_to_update = tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'base') | \
                                  tax.refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'base')
            elif config.repartition_type == 'tax':
                lines_to_update = tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax') | \
                                  tax.refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
            
            if not lines_to_update:
                 msg = "No repartition lines found for Tax %s (%s)" % (tax.name, config.repartition_type)
                 logs.append(msg)
                 continue

            # Apply Tags
            for line in lines_to_update:
                tag_to_add = config.tag_invoice_id if line.document_type == 'invoice' else config.tag_refund_id
                
                # Logic: We append the tag. 
                # Note: We do NOT clear all tags because a line might have other unrelated tags. 
                # But to avoid duplicates, Odoo handles (4, id) gracefully (it's a set).
                if tag_to_add:
                    line.write({'tag_ids': [(4, tag_to_add.id)]})
            
            success_count += 1
        
        message = _("Update Complete. Success: %s, Not Found: %s") % (success_count, error_count)
        
        if logs:
            message += "\n\nLOGS:\n" + "\n".join(logs)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("PLE Update Result"),
                'message': message,
                'sticky': False,
                'type': 'warning' if error_count > 0 else 'success',
            }
        }
