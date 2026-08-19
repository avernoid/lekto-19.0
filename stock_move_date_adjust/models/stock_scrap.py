from odoo import models


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    def _date_adjust_get_moves(self):
        return self.move_ids
