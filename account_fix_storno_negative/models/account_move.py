from odoo import Command, _, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_open_fix_storno_wizard(self):
        """Open the confirmation wizard with the selected journal entries.

        No filtering happens here: the wizard computes how many entries carry
        negatives and how many will be ignored, and the actual correction filters
        again line by line, so an entry without negatives is never counted nor
        touched.
        """
        wizard = self.env['account.fix.storno.wizard'].create({
            'move_ids': [Command.set(self.ids)],
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _("Fix Storno (negative debit/credit)"),
            'res_model': 'account.fix.storno.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    def action_fix_storno_negative(self):
        """Re-express the lines with negative debit/credit (a Storno leftover)
        to the standard positive form, over the entries in ``self``.

        The correction is purely representational: ``balance`` already holds the
        correct signed value, so we derive the standard column from it (positive
        debit when balance > 0, positive credit when balance < 0). Balance,
        amount_currency, taxes and reconciliations are untouched, so there is no
        need to reset to draft nor to re-issue the electronic document. The write
        is done in SQL on purpose, to bypass the posted-entry amount-edit lock;
        because it does not go through the ORM, no recompute is triggered that
        would revert the fix.

        Only lines with negative debit or credit are considered: an entry
        selected by mistake with no negatives contributes no lines and stays
        untouched.
        """
        lines = self.line_ids.filtered(lambda l: l.debit < 0 or l.credit < 0)
        if not lines:
            return self._notify_fix_storno(
                _("No lines with negative debit or credit in the selection."),
                'warning',
            )

        self.env.cr.execute(
            """
            UPDATE account_move_line
               SET debit  = CASE WHEN balance > 0 THEN  balance ELSE 0 END,
                   credit = CASE WHEN balance < 0 THEN -balance ELSE 0 END
             WHERE id IN %s
            """,
            (tuple(lines.ids),),
        )

        # is_storno is "sticky" (it never turns itself off): we must clear it so
        # a future recompute does not paint the negatives again. Only on the
        # entries that actually had negative lines.
        storno_moves = lines.move_id.filtered('is_storno')
        if storno_moves:
            self.env.cr.execute(
                "UPDATE account_move SET is_storno = false WHERE id IN %s",
                (tuple(storno_moves.ids),),
            )

        lines.invalidate_recordset(['debit', 'credit'])
        storno_moves.invalidate_recordset(['is_storno'])

        return self._notify_fix_storno(
            _("Fixed %(lines)s lines in %(moves)s journal entries.",
              lines=len(lines), moves=len(lines.move_id)),
            'success',
        )

    def _notify_fix_storno(self, message, notify_type):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Fix Storno"),
                'message': message,
                'type': notify_type,
                'sticky': False,
            },
        }
