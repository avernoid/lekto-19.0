from odoo import api, fields, models


class FixStornoWizard(models.TransientModel):
    _name = 'account.fix.storno.wizard'
    _description = "Fix Storno negative entries confirmation"

    move_ids = fields.Many2many(
        'account.move',
        string="Selected Entries",
        help="Journal entries selected when the fix was launched. Only those "
             "with at least one line in negative debit or credit are counted "
             "and corrected; the rest are reported as ignored.",
    )
    move_count = fields.Integer(
        string="Entries to Fix",
        compute='_compute_counts',
        help="Number of selected journal entries that contain at least one line "
             "with negative debit or credit and will therefore be corrected.",
    )
    line_count = fields.Integer(
        string="Lines to Fix",
        compute='_compute_counts',
        help="Number of journal item lines with negative debit or credit that "
             "will be re-expressed to the standard positive form (positive value "
             "in the opposite column).",
    )
    skipped_count = fields.Integer(
        string="Ignored (no negatives)",
        compute='_compute_counts',
        help="Number of selected journal entries that have no negative debit or "
             "credit line. They are neither counted nor modified.",
    )

    @api.depends('move_ids')
    def _compute_counts(self):
        for wizard in self:
            neg_lines = wizard.move_ids.line_ids.filtered(
                lambda l: l.debit < 0 or l.credit < 0
            )
            affected_moves = neg_lines.move_id
            wizard.line_count = len(neg_lines)
            wizard.move_count = len(affected_moves)
            # Selected entries that contribute no negative line: neither counted
            # nor corrected, only reported.
            wizard.skipped_count = len(wizard.move_ids) - len(affected_moves)

    def action_confirm(self):
        self.ensure_one()
        return self.move_ids.action_fix_storno_negative()
