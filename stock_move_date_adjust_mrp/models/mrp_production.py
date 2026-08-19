from odoo import models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _date_adjust_get_moves(self):
        return self.move_raw_ids | self.move_finished_ids
