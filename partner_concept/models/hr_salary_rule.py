from odoo import models



class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    def _compute_display_name(self):
        for rule in self:
            struct = rule.struct_id.name or ''
            category = rule.category_id.name or ''
            rule.display_name = f"[{struct}] {category} \u2013 {rule.name}"
