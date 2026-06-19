# Copyright 2026 Ganemo
# License OPL-1 (Odoo Proprietary License v1.0) - See LICENSE file.
from odoo import fields, models


class AccountAnalyticApplicability(models.Model):
    _inherit = "account.analytic.applicability"

    business_domain = fields.Selection(
        selection_add=[("stock_move", "Stock Move")],
        ondelete={"stock_move": "cascade"},
    )
    stock_picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type",
        help="Restrict this applicability to a specific operation type. "
        "Leave empty to apply it to every stock move.",
    )

    def _get_score(self, **kwargs):
        """Refine the score with the operation type when one is set.

        An applicability scoped to an operation type only applies to moves of
        that type; a more specific match scores higher so it wins over a
        generic stock-move rule.
        """
        score = super()._get_score(**kwargs)
        if score >= 0 and self.stock_picking_type_id:
            if kwargs.get("picking_type") == self.stock_picking_type_id.id:
                return score + 1
            return -1
        return score
