from odoo import fields, models


class IrUiMenu(models.Model):
    """
    Model to restrict the menu for specific users.
    """
    _inherit = 'ir.ui.menu'

    excluded_user_ids = fields.Many2many(
        'res.users',
        'ir_ui_menu_res_users_hidden_rel',
        'menu_id',
        'user_id',
        string="Excluded Users",
        help='Users restricted from accessing this menu.'
    )

    def write(self, vals):
        res = super().write(vals)
        if 'excluded_user_ids' in vals:
            self.env.registry.clear_cache()
        return res

    def _filter_visible_menus(self):
        """
        Override to filter out menus restricted for current user.
        Applies only to the current user context.
        """
        menus = super()._filter_visible_menus()
        
        # Odoo 19/Standard: Check for superuser or system group
        if self.env.is_superuser() or self.env.user.has_group('base.group_system'):
            return menus
            
        return menus.filtered(
            lambda menu: self.env.user.id not in menu.excluded_user_ids.sudo().ids
        )
