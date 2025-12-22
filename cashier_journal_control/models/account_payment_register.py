from odoo import models, api

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        if 'journal_id' in fields_list:
            # Logic to override journal_id default
            user = self.env.user
            
            # Domain to find candidates caused by this module's logic
            # We want to check if the *currently selected* default (from super) 
            # is valid for this user.
            # AND/OR we want to enforce our "Default Cash" logic.
            
            # Guidelines say:
            # "el wizard propondrá por defecto solo diarios: visibles para el usuario, marcados como default"
            # "si hay varios, elegir el de menor secuencia"
            # "si no hay ninguno: NO proponer diario"
            
            # First, check what journals are "visible" (allowed) for this user.
            allowed_domain = [
                ('type', 'in', ('bank', 'cash', 'credit')),
                ('company_id', '=', self.env.company.id),
                '|', ('allowed_user_ids', '=', False), ('allowed_user_ids', 'in', user.ids)
            ]
            
            # Find default cash journals within allowed ones
            default_domain = allowed_domain + [('is_default_cash', '=', True)]
            
            # Search for the best default
            # Order by sequence to respect "menor secuencia"
            suggested_journal = self.env['account.journal'].search(default_domain, limit=1, order='sequence, id')
            
            if suggested_journal:
                # If we found a specific default cash for this user, use it.
                res['journal_id'] = suggested_journal.id
            else:
                # Strict requirement: If no "Default Cash" journal is found for this user,
                # leave the field empty to force manual selection.
                res['journal_id'] = False

        return res
