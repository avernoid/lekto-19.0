from odoo import api, fields, models, _
import pytz
from odoo.exceptions import RedirectWarning, UserError, ValidationError

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ple_correlative = fields.Char(
        string='Correlativo'
    )

    def update_correlative(self, move_prefix):
        i = 1
        for line in self:
            if line.ple_correlative and line.ple_correlative != move_prefix:
                line.ple_correlative = '{}{}'.format(move_prefix, str(i).zfill(9))
            i += 1

    def update_correlative_cr(self, move_prefix, i):
        for line in self:
            if not line.ple_correlative:
                ple_correlative = '{}{}'.format(move_prefix, str(i).zfill(9))
                self.env.cr.execute("""UPDATE account_move_line
                                    SET ple_correlative=%s
                                    WHERE id=%s """,
                                 (ple_correlative, self.id))