# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    """Extension of res.users to add button visibility rules."""
    _inherit = 'res.users'
    
    button_rule_ids = fields.One2many(
        'ui.button.rule',
        'user_id',
        string='Button Visibility Rules',
        help='Configure which interface buttons to hide for this user in different contexts'
    )
    
    button_rule_count = fields.Integer(
        string='Rules Count',
        compute='_compute_button_rule_count'
    )
    
    @api.depends('button_rule_ids')
    def _compute_button_rule_count(self):
        """Compute the number of active rules for this user."""
        for user in self:
            user.button_rule_count = len(user.button_rule_ids)
    
    def get_button_rules_json(self):
        """
        Return button rules for the current user in JSON format for frontend consumption.
        
        Returns:
            dict: Rules organized by view type
        """
        self.ensure_one()
        return self.env['ui.button.rule'].get_user_rules(self.id)
