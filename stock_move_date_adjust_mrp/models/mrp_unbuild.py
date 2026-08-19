from odoo import models


class MrpUnbuild(models.Model):
    _inherit = "mrp.unbuild"

    def _date_adjust_get_moves(self):
        # `produce_line_ids` is the one2many on `unbuild_id`, which the core stamps
        # on every movement of the disassembly -- consumption included.
        # `consume_line_ids` (on `consume_unbuild_id`) is never populated by the
        # core; it is unioned here only so a third party that does populate it is
        # not left out.
        return self.produce_line_ids | self.consume_line_ids
