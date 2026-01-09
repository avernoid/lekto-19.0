from odoo import api, models, tools
from odoo.fields import Domain
from odoo.tools import config


class IrRule(models.Model):
    _inherit = "ir.rule"

    @api.model
    @tools.conditional(
        "xml" not in config["dev_mode"],
        tools.ormcache(
            "self.env.uid",
            "self.env.su",
            "model_name",
            "mode",
            "tuple(self._compute_domain_context_values())",
        ),
    )
    def _compute_domain(self, model_name, mode="read"):
        """
        This function is used to compute the domain of the ir.rule.
        It is used to restrict the records that are accessible to the user.
        The function uses the ormcache decorator to cache the result of the function based on the user's id and the model name.
        If the user is not an administrator, the function adds an extra domain to restrict the records based on the journal_assign_to_ids field.
        The function uses the Domain.AND function to combine the extra domain with the original domain.
        """
        res = super()._compute_domain(model_name, mode=mode)
        user = self.env.user
        if model_name == "account.move" and not user.has_group("add_user_by_journal.res_groups_admin_journal_access"):
             # Allow access if:
            # 4. Whitelisted INTEROPERABILITY for Secondary Entries
            # We allow reading Journal Entries (move_type='entry') if they are Payments, Bank Statements, or affect AR/AP.
            # CRITICAL: We MUST restrict this to 'entry' type to prevent "Restricted Invoices" (which also hit AR/AP) from leaking.
            whitelist_domain = Domain(['&', ('move_type', '=', 'entry'), '|', '|', ('payment_ids', '!=', False), ('statement_line_id', '!=', False), ('line_ids.account_id.account_type', 'in', ('asset_receivable', 'liability_payable'))])
            
            extra_domain = Domain(['|', '|', '&', ('journal_assign_to_ids', '=', False), ('journal_group_ids', '=', False), '|', ('journal_assign_to_ids', 'in', [user.id]), ('journal_group_ids', 'in', user.group_ids.ids), whitelist_domain])
            res = Domain.AND([extra_domain, res])
        
        elif model_name == "account.move.line" and not user.has_group("add_user_by_journal.res_groups_admin_journal_access"):
             # Mirror the logic from account.move but using fields available on account.move.line
             # We can't check 'journal_assign_to_ids' directly as it's not on the line (unless we add related field).
             # Adding a related field on the LINE table (huge) is bad performance.
             # So we must check via relations: 'journal_id.assign_to_ids' etc.
             
             # 1. Public (Both empty)
             d_public = ['&', ('journal_id.assign_to_ids', '=', False), ('journal_id.journal_group_ids', '=', False)]
             # 2. User assigned
             d_user = [('journal_id.assign_to_ids', 'in', [user.id])]
             # 3. Group allowed
             d_group = [('journal_id.journal_group_ids', 'in', user.group_ids.ids)]
             
             # 4. Whitelisted Interoperability
             # Must access move_id fields. This is slightly expensive but necessary.
             # move_id.move_type, move_id.payment_ids, move_id.statement_line_id
             # Fix Conflict: Pre-fetch account IDs to avoid implicit 'LEFT JOIN account_account' which conflicts with 
             # reports (like Cash Flow) that use explicit 'JOIN account_account'.
             allowed_account_ids = self.env['account.account'].sudo().search([
                 ('account_type', 'in', ('asset_receivable', 'liability_payable'))
             ]).ids
             d_whitelist = ['&', ('move_id.move_type', '=', 'entry'), '|', '|', ('move_id.payment_ids', '!=', False), ('move_id.statement_line_id', '!=', False), ('account_id', 'in', allowed_account_ids)]
             # Note: For AR/AP, we check the line's own account! ('account_id' in list).
             # This is actually simpler/better than checking move_id.line_ids.
             
             extra_domain = Domain(['|', '|', '|'] + d_public + d_user + d_group + d_whitelist)
             res = Domain.AND([extra_domain, res])
             
        return res
