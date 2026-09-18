import logging
from datetime import timedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = "account.general.ledger.report.handler"

    def _l10n_pe_get_lib_3_7_data(self, options, currency_table_query):
        """3.7 with the value known at the end of the period (design v4, D7).

        Why not the native figure: it sums ``stock_move.value``, and the engine writes late
        revaluations into those values.  A 3.7 of July regenerated in September would carry a
        September freight, and would no longer close on the July PLE 13.1 as filed.

        Why the cut moves one day: the native query filters ``stock_move.date < date_to`` with a
        date, i.e. before midnight of the last day, so every movement of that day is left out --
        month-end deliveries, the most common ones.  The 3.7 is the balance *at* the end of the
        period, and the 13.1 of the same period includes that day.  The native method is called
        with the next day, so its row selection, codes and names stay native and include the last
        day; ``report_date`` is set back.

        Why rows are matched by code and not by id: the native method drops the product id before
        returning.  The code it prints is the product's ``default_code`` with non-alphanumerics
        removed; SUNAT identifies the row by that code, so two products sharing it would already be
        an invalid file.  Such rows are left native and logged, never guessed.

        Quantity and value both come from ``_variance_value_known_at``: done movements only (the
        native query has no state filter), in the product unit, so the unit cost is never a value of
        one cut divided by a quantity of another.
        """
        date_to = fields.Date.to_date(options["date"]["date_to"])
        shifted = {**options, "date": {**options["date"], "date_to": fields.Date.to_string(date_to + timedelta(days=1))}}
        rows = super()._l10n_pe_get_lib_3_7_data(shifted, currency_table_query)
        report_date = fields.Date.to_string(date_to).replace("-", "")
        company_ids = self.env.ref("account_reports.general_ledger_report").get_report_company_ids(options)
        products_by_code = {}
        for product in self.env["product.product"].with_context(active_test=False).search([
                ("default_code", "!=", False), ("product_tmpl_id.l10n_pe_type_of_existence", "!=", False)]):
            code = "".join(e for e in product.default_code if e.isalnum())
            products_by_code.setdefault(code, self.env["product.product"])
            products_by_code[code] |= product
        for row in rows:
            row["report_date"] = report_date
            products = products_by_code.get(row["product_default_code"], self.env["product.product"])
            if len(products) != 1:
                _logger.warning("PLE 3.7: code %s matches %s products; row left as computed natively.",
                                row["product_default_code"], len(products))
                continue
            quantity = value = 0.0
            for company in self.env["res.company"].browse(company_ids):
                qty, val = products.with_company(company)._variance_value_known_at(date_to)
                quantity += qty
                value += val
            row["stock_quantity"] = "%.2f" % quantity
            row["stock_value"] = "%.2f" % value
            row["stock_unit_cost"] = "%.2f" % (value / quantity if quantity else 0.0)
        return [row for row in rows if row["stock_quantity"] != "0.00"]
