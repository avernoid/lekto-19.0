# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class UiButtonRule(models.Model):
    """
    Model to define button visibility rules per user.
    
    Rules are evaluated in the frontend to hide standard buttons (New, Edit, Archive, etc.)
    based on view type, model, and business context without affecting actual permissions.
    
    If no rule exists for a user, Odoo behaves 100% natively.
    """
    _name = 'ui.button.rule'
    _description = 'UI Button Visibility Rule'
    _order = 'user_id, view_type, button_name'
    
    # Core fields
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        index=True,
        help='User to whom this rule applies'
    )
    
    res_model = fields.Char(
        string='Model',
        help='Technical model name (e.g., project.task, sale.order). '
             'Leave empty to apply to all models.'
    )
    
    view_type = fields.Selection(
        [
            ('kanban', 'Kanban'),
            ('list', 'List'),
            ('form', 'Form'),
        ],
        string='View Type',
        required=True,
        help='Type of view where this rule applies'
    )
    
    button_name = fields.Selection(
        [
            ('create', 'New / Create'),
            ('edit', 'Edit'),
            ('archive', 'Archive / Unarchive'),
            ('duplicate', 'Duplicate'),
            ('export', 'Export'),
            ('import', 'Import'),
            ('delete', 'Delete'),
            ('cancel', 'Cancel'),
            ('validate', 'Validate'),
        ],
        string='Button',
        required=True,
        help='Standard button to control'
    )
    
    context_key = fields.Selection(
        [
            ('any', 'Any Context'),
            ('fsm', 'Field Service'),
            ('from_sale', 'From Sales'),
            ('readonly', 'Read-only Mode'),
        ],
        string='Business Context',
        required=True,
        default='any',
        help='Business context where this rule applies:\n'
             '• Any Context: Always applies\n'
             '• Field Service: Only in FSM views\n'
             '• From Sales: Only when invoked from sales orders\n'
             '• Read-only Mode: Only in read-only views'
    )
    
    hide = fields.Boolean(
        string='Hide Button',
        default=True,
        help='If checked, the button will be hidden when this rule applies'
    )
    
    # Computed display name
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )
    
    _unique_rule = models.Constraint(
        'UNIQUE(user_id, res_model, view_type, button_name, context_key)',
        'A rule with the same configuration already exists for this user!',
    )
    
    @api.depends('user_id', 'res_model', 'view_type', 'button_name', 'context_key', 'hide')
    def _compute_display_name(self):
        """Generate a user-friendly display name for the rule."""
        for rule in self:
            model_part = rule.res_model or _('All Models')
            action = _('Hide') if rule.hide else _('Show')
            rule.display_name = f"{action} {dict(rule._fields['button_name'].selection).get(rule.button_name)} " \
                               f"in {dict(rule._fields['view_type'].selection).get(rule.view_type)} " \
                               f"({model_part}) - {dict(rule._fields['context_key'].selection).get(rule.context_key)}"
    
    @api.constrains('res_model')
    def _check_res_model(self):
        """Validate that res_model exists if provided."""
        for rule in self:
            if rule.res_model:
                if not self.env['ir.model'].search([('model', '=', rule.res_model)], limit=1):
                    raise ValidationError(
                        _('The model "%s" does not exist in the system.') % rule.res_model
                    )
    
    @api.model
    def get_user_rules(self, user_id):
        """
        Get all active rules for a specific user.
        
        Args:
            user_id (int): ID of the user
            
        Returns:
            dict: Rules grouped by view_type for efficient lookup
        """
        rules = self.search([('user_id', '=', user_id), ('hide', '=', True)])
        
        result = {
            'kanban': [],
            'list': [],
            'form': []
        }
        
        for rule in rules:
            result[rule.view_type].append({
                'button_name': rule.button_name,
                'res_model': rule.res_model or False,
                'context_key': rule.context_key,
            })
        
        return result
