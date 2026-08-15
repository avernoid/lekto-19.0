from odoo import models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def _cal_cost(self, date=False):
        """Leave the flagged work centres out, only while the labour entry is built.

        The context flag is set by ``mrp.production._post_labour()`` and by nothing
        else, so every other caller keeps seeing the real cost: ``_cal_price()``,
        which puts the operations into the value of the manufactured product, and
        the WIP accounting wizard, which passes a cut-off ``date``.

        The signature mirrors the native one (``date`` included, and forwarded) and
        the method stays multi-record: it filters the recordset and delegates,
        instead of returning a scalar for the whole set.
        """
        if not self.env.context.get("reclass_skip_labour_entry"):
            return super()._cal_cost(date)
        booked = self.filtered(
            lambda workorder: not workorder.workcenter_id.reclass_skip_labour_entry)
        if not booked:
            return 0.0
        return super(MrpWorkorder, booked)._cal_cost(date)
