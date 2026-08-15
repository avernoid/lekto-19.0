import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _post_labour(self):
        """Let the flagged work centres out of the labour entry.

        Native ``_post_labour`` has no seam to restrict the work orders: it walks
        ``mo.workorder_ids`` and adds ``wo._cal_cost()`` for each. Instead of
        reimplementing it -- which would freeze a copy of native code -- the cost of
        the flagged work centres is neutralised **only for the duration of this
        call**, through a context flag read by ``mrp.workorder._cal_cost()``.

        Consequences, all of them native behaviour:

        * if every work centre of the order is flagged, the total is zero and the
          native guard ``if currency.is_zero(workcenter_cost): continue`` skips the
          entry altogether;
        * ``_cal_price`` calls ``_cal_cost()`` without that context, so the value of
          the manufactured product is exactly the same as without this module.
        """
        flagged = self.workorder_ids.filtered(
            lambda wo: wo.workcenter_id.reclass_skip_labour_entry)
        if not flagged:
            return super()._post_labour()
        _logger.info(
            "Reclassification: %s work order(s) left out of the labour entry of %s",
            len(flagged), ", ".join(self.mapped("name")))
        return super(
            MrpProduction, self.with_context(reclass_skip_labour_entry=True)
        )._post_labour()
