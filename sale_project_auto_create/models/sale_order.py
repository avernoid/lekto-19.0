# Part of Ganemo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    auto_create_project = fields.Boolean(
        string="Create Project on Confirmation",
        compute="_compute_auto_create_project",
        store=True,
        readonly=False,
        help="When enabled, confirming this order creates a project linked to it "
        "(with its analytic account) without needing a service product line. "
        "It defaults from the sales team and can be overridden here. It is "
        "ignored when the order already has a project or when a service product "
        "already makes Odoo generate one natively.",
    )

    @api.depends("team_id")
    def _compute_auto_create_project(self):
        for order in self:
            order.auto_create_project = order.team_id.auto_create_project

    def _auto_create_project_eligible(self):
        """Return True when this order must auto-generate a project on confirmation.

        The check is deliberately conservative so it never collides with the
        native ``sale_project`` generation: if any line is a service product
        configured to generate a project/task (native flow), or the order
        already has a project, we stay out of the way.
        """
        self.ensure_one()
        if not self.auto_create_project or self.project_id:
            return False
        # Defer to the native generation whenever it would produce/assign a
        # project itself. We reuse sale_project's own helpers so we follow
        # upstream's definition of "this line generates a project" rather than
        # re-deriving it.
        native_lines = (
            self.order_line._get_so_lines_new_project()
            | self.order_line._get_so_lines_task_global_project()
        )
        return not native_lines

    def _auto_create_project_values(self):
        """Project creation values, mirroring the native sale-driven flow."""
        self.ensure_one()
        account = self.project_account_id or self.env[
            "account.analytic.account"
        ].sudo().create(self._prepare_analytic_account_data())
        return {
            "name": self.name,
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "allow_billable": True,
            "account_id": account.id,
            # Linking the order here makes project.project.create() wire
            # order.project_id back automatically; we still set it explicitly
            # below to stay resilient if that native behaviour ever changes.
            "reinvoiced_sale_order_id": self.id,
        }

    def _auto_create_project(self):
        """Create the policy-driven project for every eligible order."""
        for order in self:
            if not order._auto_create_project_eligible():
                continue
            order_sudo = order.sudo()
            project = (
                self.env["project.project"]
                .sudo()
                .create(order_sudo._auto_create_project_values())
            )
            if not order_sudo.project_id:
                order_sudo.project_id = project.id

    def _action_confirm(self):
        # Run before the native confirmation so the stock procurement (which
        # reads order.project_id) carries the project exactly like the native
        # service-product flow does. Eligibility guarantees we never duplicate
        # a project that sale_project is about to create.
        self._auto_create_project()
        return super()._action_confirm()
