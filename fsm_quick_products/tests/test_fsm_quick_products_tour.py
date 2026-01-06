# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, HttpCase

@tagged('post_install', '-at_install')
class TestFsmQuickProductsTour(HttpCase):

    def test_fsm_quick_products_tour(self):
        # Create test data to ensure the tour has something to work with
        partner = self.env['res.partner'].create({'name': 'Test Customer'})
        
        project = self.env['project.project'].create({
            'name': 'FSM Test Project',
            'is_fsm': True,
            'allow_billable': True,
            'company_id': self.env.company.id,
        })
        
        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
        })
        
        task = self.env['project.task'].create({
            'name': 'Fsm test task',
            'project_id': project.id,
            'partner_id': partner.id,
            'sale_order_id': sale_order.id,
        })

        self.start_tour("/odoo", 'fsm_quick_products_tour', login="admin")
