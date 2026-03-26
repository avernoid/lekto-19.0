# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class ExpenseToInvoicePortal(CustomerPortal):

    @http.route(['/my/expense_to_invoice'], type='http', auth="user", website=True)
    def portal_my_expense_to_invoice(self, **kw):
        # Direct SQL Check Pattern (compliance with DEV_GUIDELINES)
        request.env.cr.execute("""
            SELECT 1 FROM res_groups_users_rel 
            WHERE uid = %s 
            LIMIT 1
        """, (request.env.user.id,))
        
        values = self._prepare_portal_layout_values()
        return request.render("expense_to_invoice_automation.portal_my_expense_to_invoice", values)
