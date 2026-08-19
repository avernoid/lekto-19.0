from collections import defaultdict

from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _date_adjust_origin(self):
        self.ensure_one()
        # Manufacturing movements never carry a transfer, so testing them first
        # cannot shadow the base classification.
        if self.raw_material_production_id:
            return "production_raw", self.raw_material_production_id
        if self.production_id:
            return "production_finished", self.production_id
        # The core never assigns `consume_unbuild_id` -- both generators stamp
        # `unbuild_id` on every movement, consumption included. It is read here
        # defensively only.
        if self.unbuild_id:
            return "unbuild", self.unbuild_id
        if self.consume_unbuild_id:
            return "unbuild", self.consume_unbuild_id
        return super()._date_adjust_origin()

    @api.model
    def _date_adjust_origin_labels(self):
        labels = super()._date_adjust_origin_labels()
        labels.update({
            "production_raw": self.env._("Manufacturing - Components"),
            "production_finished": self.env._("Manufacturing - Finished Product"),
            "unbuild": self.env._("Disassembly"),
        })
        return labels

    def _date_adjust_stagger_rank(self):
        self.ensure_one()
        origin, _document = self._date_adjust_origin()
        if origin == "production_raw":
            return 0
        if origin == "production_finished":
            return 1
        if origin == "unbuild":
            # Consumption of the finished product first, return of components after.
            return 1 if self.is_in else 0
        return super()._date_adjust_stagger_rank()

    def _date_adjust_cascade_siblings(self):
        siblings = super()._date_adjust_cascade_siblings()
        for move in self:
            origin, document = move._date_adjust_origin()
            if origin == "production_raw":
                siblings |= document.move_raw_ids
            elif origin == "production_finished":
                siblings |= document.move_finished_ids
        return siblings - self

    def _date_adjust_sync_document(self, target_by_move):
        starts = defaultdict(list)
        finishes = defaultdict(list)
        for move in self:
            origin, document = move._date_adjust_origin()
            if origin == "production_raw":
                starts[document].append(target_by_move[move])
            elif origin == "production_finished":
                finishes[document].append(target_by_move[move])

        for production in set(starts) | set(finishes):
            vals = {}
            if production in starts:
                vals["date_start"] = min(starts[production])
            if production in finishes:
                vals["date_finished"] = max(finishes[production])
            if not vals:
                continue
            if production.state in ("done", "cancel"):
                # `force_date` lifts the "you cannot move a done order" guard and
                # the automatic unplanning. The core reserves it for its own
                # work-order planner; on a done order it is the only way through.
                production.with_context(force_date=True).write(vals)
            else:
                # Still open: let the native unplanning run, it is the correct
                # behaviour when the order is planned.
                production.write(vals)

        return super()._date_adjust_sync_document(target_by_move)
