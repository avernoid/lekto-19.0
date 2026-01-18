from odoo import models, api, _
from num2words import num2words


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('amount_total', 'currency_id', 'journal_id.amount_text_format',
                 'journal_id.amount_text_in_caps', 'journal_id.amount_text_lang_id', 'partner_id.lang')
    def _compute_amount_total_words(self):
        # Separate records by format configuration to optimize
        # Logic Change: We explicitly filter for OUR custom format.
        # Everything else (Native, or future formats added by other modules) falls through to super().
        custom_moves = self.filtered(lambda m: m.journal_id.amount_text_format == 'custom')
        other_moves = self - custom_moves

        # 1. Handle Native/Other Formats (call super)
        if other_moves:
            super(AccountMove, other_moves)._compute_amount_total_words()

        # 2. Handle Custom Format (00/100)
        for move in custom_moves:
            # Determine language
            lang_code = move.journal_id.amount_text_lang_id.code or move.partner_id.lang or self.env.user.lang or 'es_PE'
            # num2words uses strict codes mostly for 'es', 'en', etc. 
            # We map full locale to num2words lang code if necessary, or pass full code (num2words handles many)
            num2words_lang = lang_code[:2] if lang_code else 'es'
            
            # Ensure strict context for translation
            move_with_lang = move.with_context(lang=lang_code)

            amount_i, amount_d = divmod(move.amount_total, 1)
            amount_d = int(round(amount_d * 100, 2))
            
            try:
                words = num2words(amount_i, lang=num2words_lang)
            except NotImplementedError:
                # Fallback to english if language not supported by num2words
                words = num2words(amount_i, lang='en')

            # Translate connector using Odoo's native mechanism
            # This ' AND ' will be looked up in the PO files for the target language
            connector = move_with_lang.env._(' AND ')
            if not move.journal_id.amount_text_in_caps:
                connector = connector.lower()
            
            # Currency unit label (e.g., SOLES, DOLLARS)
            currency_name = move.currency_id.currency_unit_label or move.currency_id.name

            # Format: "ONE HUNDRED AND 50/100 DOLLARS"
            result = '%(words)s%(connector)s%(amount_d)02d/100 %(currency_name)s' % {
                'words': words,
                'connector': connector,
                'amount_d': amount_d,
                'currency_name': currency_name,
            }
            
            move.amount_total_words = result

        # 3. Apply Casing / Upper Override (common for both Native and Custom if requested)
        # We re-iterate all because Native users might ALSO want Uppercase enforced
        for move in self:
            if move.amount_total_words and move.journal_id.amount_text_in_caps:
                move.amount_total_words = move.amount_total_words.upper()
            elif move.amount_total_words and not move.journal_id.amount_text_in_caps:
                # Optional: Ensure Capitalize if strictness is required, but usually native is already good.
                # Only force Capitalize if it was Custom, to avoid altering native too much if not asked.
                if move.journal_id.amount_text_format == 'custom':
                    # Only capitalize the first letter, keeping the rest (e.g. 'DOLLARS') as is
                    val = move.amount_total_words
                    if val:
                        move.amount_total_words = val[0].upper() + val[1:]

    # Deprecated but kept for backward compatibility with old calls
    def _amount_to_text(self):
        self.ensure_one()
        return self.amount_total_words
