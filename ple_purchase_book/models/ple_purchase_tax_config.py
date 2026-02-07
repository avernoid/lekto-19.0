from odoo import api, fields, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class PlePurchaseTaxConfig(models.Model):
    _name = 'ple.purchase.tax.config'
    _description = 'PLE Purchase Tax Configuration'

    name = fields.Char(string='Name', required=True)
    tax_xml_prefix = fields.Char(string='XML Prefix', required=True, default='account', help="Prefix of the External ID (e.g., 'account' or 'l10n_pe')")
    tax_xml_suffix = fields.Char(string='XML Suffix', required=True, help="Suffix of the External ID without Company ID (e.g., 'igv_18_dua')")
    repartition_type = fields.Selection([
        ('base', 'Base'),
        ('tax', 'Tax'),
    ], string='Repartition Type', required=True)
    
    tag_invoice_id = fields.Many2one('account.account.tag', string='Invoice Tag', help="Tag for Purchase Invoices")
    tag_refund_id = fields.Many2one('account.account.tag', string='Refund Tag', help="Tag for Credit Notes (Refunds)")

    def _get_tax_xml_id(self, company_id):
        """Constructs the expected XML ID for the current company."""
        self.ensure_one()
        return f"{self.tax_xml_prefix}.{company_id}_{self.tax_xml_suffix}"

    def action_update_tags_wizard(self):
        """ Opens the wizard with this record pre-selected """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Update PLE Purchase Tags',
            'res_model': 'ple.update.purchase.tags.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_config_ids': [self.id],
            }
        }


class PleUpdatePurchaseTagsWizard(models.TransientModel):
    _name = 'ple.update.purchase.tags.wizard'
    _description = 'Wizard to specific Update PLE Tags'

    def action_update_tags(self):
        """
        Iterates over all tax configurations and applies tags by searching for them by name.
        """
        config_model = self.env['ple.purchase.tax.config']
        current_company = self.env.company
        
        configs = config_model.search([('company_id', '=', current_company.id)])
        
        if not configs:
            raise UserError(f"No configuration rules found for company {current_company.name}. Please configure them first.")

        updated_count, errors = configs.action_update_tags()

        if errors:
            message = f"Update completed with {updated_count} taxes updated.\n\nWARNINGS:\n" + "\n".join(errors)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Partial Success',
                    'message': message,
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Successfully updated tags for {updated_count} taxes.',
                'type': 'success',
                'sticky': False,
            }
        }

        if errors:
            message = f"Update completed with {updated_count} taxes updated.\n\nWARNINGS:\n" + "\n".join(errors)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Partial Success',
                    'message': message,
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Successfully updated tags for {updated_count} taxes.',
                'type': 'success',
                'sticky': False,
            }
        }
