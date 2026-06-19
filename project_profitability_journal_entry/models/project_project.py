# Part of Ganemo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, models

# Profitability section identifiers. Sequences place them next to the other
# cost / revenue rows of the panel (costs sit in the high teens / twenties,
# revenues in the single digits / low teens in the native modules).
COST_SECTION = "journal_entry_costs"
REVENUE_SECTION = "journal_entry_revenues"
COST_SEQUENCE = 19
REVENUE_SEQUENCE = 10


class ProjectProject(models.Model):
    _inherit = "project.project"

    # ------------------------------------------------------------------
    #  Profitability: manual journal entries
    # ------------------------------------------------------------------

    def _journal_entry_profitability_domain(self):
        """Analytic items to add to the panel.

        Restricted to items that come from a *posted journal entry*
        (``move_type = 'entry'``). This set is disjoint from every native
        profitability source -- customer invoices (sale move types), vendor
        bills (purchase move types) and timesheets (analytic items with no
        journal item) -- so adding it can never double count.
        """
        self.ensure_one()
        return [
            ("account_id", "in", self.account_id.ids),
            ("move_line_id", "!=", False),
            ("move_line_id.parent_state", "=", "posted"),
            ("move_line_id.move_id.move_type", "=", "entry"),
        ]

    def _journal_entry_section_action(self, section_id, line_ids):
        """Reuse the native ``action_profitability_items`` dispatcher so the
        section is clickable and opens the underlying analytic items."""
        return {
            "name": "action_profitability_items",
            "type": "object",
            "args": json.dumps([section_id, [("id", "in", line_ids)]]),
        }

    def _get_journal_entry_profitability_items(self, with_action=True):
        self.ensure_one()
        result = {
            "costs": {"data": [], "total": {"billed": 0.0, "to_bill": 0.0}},
            "revenues": {"data": [], "total": {"invoiced": 0.0, "to_invoice": 0.0}},
        }
        if not self.account_id:
            return result
        currency = self.currency_id or self.company_id.currency_id or self.env.company.currency_id
        company = self.company_id or self.env.company
        read_group = self.env["account.analytic.line"].sudo()._read_group(
            self._journal_entry_profitability_domain(),
            ["currency_id"],
            ["amount:sum", "id:array_agg"],
        )
        billed = invoiced = 0.0
        cost_ids, revenue_ids = [], []
        for line_currency, amount_sum, ids in read_group:
            amount = amount_sum
            if line_currency and line_currency != currency:
                amount = line_currency._convert(amount_sum, currency, company)
            if currency.is_zero(amount):
                continue
            if amount < 0:  # expense booked on the analytic account -> cost
                billed += amount
                cost_ids += ids
            else:  # income booked on the analytic account -> revenue
                invoiced += amount
                revenue_ids += ids
        if cost_ids:
            data = {
                "id": COST_SECTION,
                "sequence": COST_SEQUENCE,
                "billed": billed,
                "to_bill": 0.0,
            }
            if with_action:
                data["action"] = self._journal_entry_section_action(COST_SECTION, cost_ids)
            result["costs"]["data"].append(data)
            result["costs"]["total"]["billed"] = billed
        if revenue_ids:
            data = {
                "id": REVENUE_SECTION,
                "sequence": REVENUE_SEQUENCE,
                "invoiced": invoiced,
                "to_invoice": 0.0,
            }
            if with_action:
                data["action"] = self._journal_entry_section_action(REVENUE_SECTION, revenue_ids)
            result["revenues"]["data"].append(data)
            result["revenues"]["total"]["invoiced"] = invoiced
        return result

    def _get_profitability_items(self, with_action=True):
        # Additive on purpose: take whatever the stack already produced (with or
        # without Sales / Timesheet layers) and append our own section. Running
        # super() first makes this resilient to the MRO order -- our section is
        # added exactly once regardless of which other modules are installed.
        profitability_items = super()._get_profitability_items(with_action)
        if (
            not isinstance(profitability_items, dict)
            or "costs" not in profitability_items
            or "revenues" not in profitability_items
        ):
            return profitability_items
        for project in self:
            extra = project._get_journal_entry_profitability_items(with_action)
            profitability_items["costs"]["data"] += extra["costs"]["data"]
            profitability_items["costs"]["total"]["billed"] += extra["costs"]["total"]["billed"]
            profitability_items["costs"]["total"]["to_bill"] += extra["costs"]["total"]["to_bill"]
            profitability_items["revenues"]["data"] += extra["revenues"]["data"]
            profitability_items["revenues"]["total"]["invoiced"] += extra["revenues"]["total"]["invoiced"]
            profitability_items["revenues"]["total"]["to_invoice"] += extra["revenues"]["total"]["to_invoice"]
        return profitability_items

    def _get_profitability_labels(self):
        return {
            **super()._get_profitability_labels(),
            COST_SECTION: _("Other Costs (Journal Entries)"),
            REVENUE_SECTION: _("Other Revenues (Journal Entries)"),
        }

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        if section_name in (COST_SECTION, REVENUE_SECTION):
            return {
                "name": _("Journal Entry Analytic Items"),
                "type": "ir.actions.act_window",
                "res_model": "account.analytic.line",
                "views": [[False, "list"], [False, "form"]],
                "domain": domain or [],
                "context": {"create": False, "edit": False},
            }
        return super().action_profitability_items(section_name, domain=domain, res_id=res_id)
