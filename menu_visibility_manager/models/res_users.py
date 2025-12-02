from odoo import api, fields, models, Command


class ResUsers(models.Model):
    """
    Model to handle hiding specific menu items for certain users.
    """
    _inherit = 'res.users'

    hidden_menu_ids = fields.Many2many(
        'ir.ui.menu',
        'ir_ui_menu_res_users_hidden_rel',
        'user_id',
        'menu_id',
        string="Hidden Menus",
        help='Select menu items that need to be hidden from this user.'
    )

    def write(self, vals):
        """
        Override write to handle group changes logic safely.
        """
        res = super().write(vals)
        
        if 'hidden_menu_ids' in vals:
            self.env.registry.clear_cache()
        
        # If user loses 'base.group_user' (Internal User), clear hidden menus
        # This logic is safe from side effects as it runs only on write
        group_user = self.env.ref('base.group_user', raise_if_not_found=False)
        if group_user:
            for user in self:
                if group_user not in user.group_ids and user.hidden_menu_ids:
                    user.hidden_menu_ids = [Command.clear()]
                    
        return res
