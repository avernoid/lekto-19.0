from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _date_adjust_get_moves(self):
        return self.move_ids
