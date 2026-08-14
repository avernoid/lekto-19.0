from odoo import api, fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    reclass_production_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Production/Consumption Account",
        company_dependent=True,
        ondelete="restrict",
        check_company=True,
        help="Cost of production / direct consumption account for the products "
             "of this category (e.g. 60211, 61211, 65).\n\n"
             "When set, the NATIVE accounting entry of a production movement "
             "(component consumption or finished goods) books its counterpart against "
             "this account instead of the account of the production location. Nothing "
             "else changes: no extra entry, no extra movement, same amount and same "
             "direction.\n\n"
             "When empty, the account is looked up on the parent category, then on its "
             "own parent, and so on. If no ancestor defines one, the native account of "
             "the location is used, exactly as without this module.\n\n"
             "Note: the movement must be valued in real time (perpetual) for an entry "
             "to exist at all; in periodic valuation Odoo books at closing.",
    )
    reclass_effective_production_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Effective Production/Consumption Account",
        compute="_compute_reclass_effective_production_account_id",
        help="Read-only. Account actually used by the production entries of this "
             "category: the one defined above, or the one inherited from the closest "
             "ancestor category that defines it. Empty means no category in the chain "
             "defines an account and the native account of the production location is "
             "used.",
    )

    @api.depends_context("company")
    @api.depends("reclass_production_account_id", "parent_id")
    def _compute_reclass_effective_production_account_id(self):
        for category in self:
            category.reclass_effective_production_account_id = (
                category._reclass_get_production_account()
            )

    def _reclass_get_production_account(self):
        """Resolve the production/consumption account for this category.

        Walks up the ``parent_id`` chain until a category defines
        ``reclass_production_account_id``.

        :return: the ``account.account`` record, or an empty recordset when no
                 ancestor defines one. It never raises, so no flow is interrupted.
        """
        self.ensure_one()
        empty = self.env["account.account"]
        category = self
        # ``parent_id`` cannot loop (native _check_category_recursion), but we keep a
        # visited set so a corrupted hierarchy can never spin forever.
        visited = set()
        while category and category.id not in visited:
            visited.add(category.id)
            if category.reclass_production_account_id:
                return category.reclass_production_account_id
            category = category.parent_id
        return empty
