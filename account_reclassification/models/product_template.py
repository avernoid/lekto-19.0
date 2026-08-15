from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    reclass_production_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Production/Consumption Account",
        company_dependent=True,
        ondelete="restrict",
        check_company=True,
        help="Cost of production / direct consumption account for this product "
             "specifically.\n\n"
             "It has priority over the account of the product category: use it to "
             "single out one product without creating a category for it. When empty, "
             "the category chain applies (category, then its parents), and if no "
             "ancestor defines one, the native account of the production location is "
             "used.",
    )
    reclass_effective_production_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Effective Production/Consumption Account",
        compute="_compute_reclass_effective_production_account_id",
        help="Read-only. Account actually used for this product, resolved as "
             "product, then category and its ancestors.",
    )

    @api.depends_context("company")
    @api.depends("reclass_production_account_id", "categ_id")
    def _compute_reclass_effective_production_account_id(self):
        for template in self:
            template.reclass_effective_production_account_id = (
                template._reclass_get_production_account()
            )

    def _reclass_get_production_account(self):
        """Resolve the production/consumption account for this product.

        Priority: the product itself, then the category chain.

        :return: the ``account.account`` record, or an empty recordset. Never raises.
        """
        self.ensure_one()
        if self.reclass_production_account_id:
            return self.reclass_production_account_id
        if self.categ_id:
            return self.categ_id._reclass_get_production_account()
        return self.env["account.account"]


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _reclass_get_production_account(self):
        """Variant-level entry point; delegates to the template."""
        self.ensure_one()
        return self.product_tmpl_id._reclass_get_production_account()
