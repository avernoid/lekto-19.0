from odoo import fields, models

RECOGNITION_HELP = (
    "Account credited, in the entry that recognises the manufactured product, for "
    "the part of the cost coming from THIS product when it is consumed as a "
    "non-storable component.\n\n"
    "A non-storable component ('Goods without tracking') is never capitalised: its "
    "purchase already went to expense. Its cost still lands in the value of the "
    "finished product, and that credit is what neutralises the expense. Giving it "
    "its own account lets you compare the expense of a specific process against "
    "the cost it added to production, and read the difference as a standard cost "
    "deviation.\n\n"
    "When empty, the account of the product category applies, then that of its "
    "ancestors, and finally the native account of the production location."
)

OPERATIONS_HELP = (
    "Account credited, in the entry that recognises the manufactured product, for "
    "the part of the cost coming from work centre operations.\n\n"
    "Leave it empty to keep the native behaviour: the operations land in the "
    "account of the production location, where the labour entry clears them.\n\n"
    "Set it to a recognition account when the labour entry is suppressed for those "
    "work centres: the credit then neutralises the payroll expense already booked "
    "by nature.\n\n"
    "This account is always used once it is set. Setting it while the labour entry "
    "is still posted leaves that entry's debit on the account of the production "
    "location; keeping both settings coherent is up to you.\n\n"
    "When empty, the account of the product category applies, then that of its "
    "ancestors, and finally the account of the production location."
)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    reclass_recognition_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Production Recognition Account",
        company_dependent=True,
        ondelete="restrict",
        check_company=True,
        help=RECOGNITION_HELP,
    )
    reclass_operations_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Production Operations Account",
        company_dependent=True,
        ondelete="restrict",
        check_company=True,
        help=OPERATIONS_HELP,
    )

    def _reclass_get_recognition_account(self):
        """Recognition account for this product: product, then category chain."""
        self.ensure_one()
        if self.reclass_recognition_account_id:
            return self.reclass_recognition_account_id
        if self.categ_id:
            return self.categ_id._reclass_get_recognition_account()
        return self.env["account.account"]

    def _reclass_get_operations_account(self):
        """Operations account for this product: product, then category chain."""
        self.ensure_one()
        if self.reclass_operations_account_id:
            return self.reclass_operations_account_id
        if self.categ_id:
            return self.categ_id._reclass_get_operations_account()
        return self.env["account.account"]


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _reclass_get_recognition_account(self):
        self.ensure_one()
        return self.product_tmpl_id._reclass_get_recognition_account()

    def _reclass_get_operations_account(self):
        self.ensure_one()
        return self.product_tmpl_id._reclass_get_operations_account()


class ProductCategory(models.Model):
    _inherit = "product.category"

    reclass_recognition_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Production Recognition Account",
        company_dependent=True,
        ondelete="restrict",
        check_company=True,
        help=RECOGNITION_HELP,
    )
    reclass_operations_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Production Operations Account",
        company_dependent=True,
        ondelete="restrict",
        check_company=True,
        help=OPERATIONS_HELP,
    )

    def _reclass_get_recognition_account(self):
        """Walk up the category tree looking for a recognition account."""
        return self._reclass_walk_up("reclass_recognition_account_id")

    def _reclass_get_operations_account(self):
        """Walk up the category tree looking for an operations account."""
        return self._reclass_walk_up("reclass_operations_account_id")

    def _reclass_walk_up(self, field_name):
        """Closest ancestor (self included) that defines ``field_name``, or empty."""
        self.ensure_one()
        category = self
        visited = set()
        while category and category.id not in visited:
            visited.add(category.id)
            if category[field_name]:
                return category[field_name]
            category = category.parent_id
        return self.env["account.account"]
