import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class StockValuationRecalcAuditDemo(models.Model):
    """Demo data: stock whose history nobody corrected, which is what this module is for.

    The scenario is built with the revaluation engine **switched off** (``variance_skip_engine``), the
    same way the module's own tests simulate history from before the engine was installed. So the
    delivery keeps the cost it had before the freight arrived and the valued Kardex ends up above the
    inventory, exactly as it does in a database that ran for months without it.

    Whoever opens the instance can then select those movements, run *Rebuild Stock Valuation* and see
    the audit with the value before and after. Without this data the wizard has nothing to rebuild and
    there is no way to tell what it does.
    """

    _inherit = "stock.valuation.recalc.audit"

    PRODUCT_CODE = "TAB-DIST-12"

    @api.model
    def _valuation_rebuild_build_demo(self):
        """Build the uncorrected history. Idempotent and never fatal."""
        if self.env["product.product"].search_count([("default_code", "=", self.PRODUCT_CODE)]):
            return
        try:
            # The engine is the one that would correct the exit at the moment of the event: with it
            # off, the landed cost only reaches the units still in stock and the delivery keeps its
            # old value -- the history this module rebuilds.
            builder = self.env["stock.value.revaluation"].with_context(variance_skip_engine=True)
            product = builder._variance_demo_product(
                self.PRODUCT_CODE, "Tablero de distribucion trifasico 12 polos", 800.0, 1500.0)
            purchase = builder._variance_demo_purchase(
                product, 4, 800.0, "Comercial Electrica Villaran S.A.C.", bill=True)
            builder._variance_demo_sale(product, 2, invoice=True)
            builder._variance_demo_landed_cost(purchase, 200.0)
        except Exception:  # noqa: BLE001 - demo data must never break an install
            _logger.warning("stock_valuation_avco_recalc: demo data could not be built", exc_info=True)
