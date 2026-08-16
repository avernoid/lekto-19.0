import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    variance_line_ids = fields.One2many(
        "stock.value.variance", "move_id", string="Value Variances",
        help="Revaluations recorded on this movement after it was done: a "
             "landed cost or a vendor bill that changed its value, split into "
             "the part still in stock and the part belonging to goods already "
             "gone.")
    variance_count = fields.Integer(
        string="Value Variance Count", compute="_compute_variance_count",
        help="How many revaluations have been recorded on this movement.")

    @api.depends("variance_line_ids")
    def _compute_variance_count(self):
        for move in self:
            move.variance_count = len(move.variance_line_ids)

    def action_view_value_variances(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Value Variances"),
            "res_model": "stock.value.variance",
            "view_mode": "list,form",
            "domain": [("move_id", "=", self.id)],
            "context": {"default_move_id": self.id},
        }

    # ------------------------------------------------------------------
    @api.model
    def _variance_remaining_by_move(self, product, company, lot=None):
        """Remaining quantity per move, **all in the product's unit**.

        Deliberately does not use ``move.remaining_qty``.  Its source,
        ``_get_remaining_moves``, builds a dict that mixes units within itself:

            qty_by_move = {m: m.quantity for m in moves[1:]}   # move's own UoM
            qty_by_move[moves[0]] = remaining_qty              # product UoM

        so a receipt booked in kilos against a product stocked in grams yields a
        ratio off by the UoM factor -- and which of the two units you get
        depends on whether the move happens to sit at the bottom of the FIFO
        stack.  Rebuilding from the stack keeps the numbers identical to the
        core's while giving one consistent unit.
        """
        product = product.with_company(company).with_context(
            allowed_company_ids=company.ids)
        stack, qty_on_first = product._run_fifo_get_stack(lot=lot)
        remaining = {}
        if not stack:
            return remaining
        for move in stack[1:]:
            remaining[move.id] = move._get_valued_qty(lot=lot) if lot else move._get_valued_qty()
        remaining[stack[0].id] = qty_on_first
        return remaining

    def _variance_has_manual_value(self):
        """True when a manual product.value pins this move's valuation.

        ``_get_value_data`` sets ``add_extra_value = False`` as soon as
        ``_get_manual_value`` returns a quantity, so the landed cost never
        reached ``move.value`` for such a move.
        """
        self.ensure_one()
        return bool(self.env["product.value"].sudo().search_count(
            [("move_id", "=", self.id)], limit=1))

    def _variance_log_manual_skip(self, cost):
        """A pinned move is not benign: in perpetual the core still capitalises
        part of the landed cost while the move's value excludes it entirely."""
        self.ensure_one()
        _logger.warning(
            "stock.value.variance: move %s is pinned by a manual product.value, "
            "so landed cost %s never entered its value. No variance recorded; "
            "if this company values in real time, the posted entry and the "
            "ledger diverge by the capitalised part.",
            self.id, cost.display_name,
        )
