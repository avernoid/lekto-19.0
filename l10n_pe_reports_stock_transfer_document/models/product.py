import re

from odoo import api, fields, models

# Scrub for field 7, cut at 24, whatever the source.  It is NOT the native one:
# v19.0.3.0.1 (task 69361) deliberately KEEPS the hyphen -- the client's own
# codes carry it ('IH-21114') and the native scrub was mangling them -- and
# strips the asterisk instead.  Reverting to the native set would silently undo
# that, so the rule lives here with its own test.
EXISTENCE_CODE_SCRUB = re.compile(r"[_/*]")

# Field 5 (Table 13) proposed for each source.  A proposal, not a rule: a
# client's internal reference may itself be a GTIN or a UNSPSC, and then the
# user overrides the catalogue without changing the source.
CATALOGUE_BY_SOURCE = {
    'internal_reference': '9',
    'barcode': '3',
    'unspsc': '1',
}


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pe_existence_code_source = fields.Selection(
        [
            ('internal_reference', 'Internal Reference'),
            ('barcode', 'Barcode'),
            ('unspsc', 'UNSPSC'),
        ],
        string='Existence Code Source',
        default='internal_reference',
        help="Which field feeds the existence code (field 7) of the PLE 12.1 "
             "and 13.1 books. If the chosen field is empty the code is left "
             "empty and SUNAT rejects the file: no other field is used as a "
             "fallback, because a file that passes validation carrying the "
             "wrong code is worse than a rejected one.",
    )
    l10n_pe_existence_catalogue = fields.Selection(
        [
            ('1', '1 - United Nations (UNSPSC)'),
            ('3', '3 - GTIN'),
            ('9', '9 - Others'),
        ],
        string='Declared Catalogue',
        compute='_compute_l10n_pe_existence_catalogue',
        store=True,
        readonly=False,
        help="SUNAT Table 13 catalogue the existence code belongs to (field 5 "
             "of the PLE 12.1 and 13.1 books). Proposed from the code source "
             "and editable: change it when the internal reference is itself a "
             "GTIN or a UNSPSC code. Changing the source proposes the "
             "catalogue again.",
    )
    l10n_pe_ple_existence_code = fields.Char(
        string='Code Sent to the PLE',
        compute='_compute_l10n_pe_ple_existence_code',
        help="Preview of what the PLE books will carry in field 7, already "
             "scrubbed and cut to 24 characters, together with the catalogue "
             "declared in field 5. The code belongs to the variant, the "
             "configuration to the product.",
    )

    @api.depends('l10n_pe_existence_code_source')
    def _compute_l10n_pe_existence_catalogue(self):
        for template in self:
            source = template.l10n_pe_existence_code_source or 'internal_reference'
            template.l10n_pe_existence_catalogue = CATALOGUE_BY_SOURCE.get(source, '9')

    @api.depends('l10n_pe_existence_code_source', 'l10n_pe_existence_catalogue',
                 'product_variant_ids.default_code', 'product_variant_ids.barcode',
                 'unspsc_code_id')
    def _compute_l10n_pe_ple_existence_code(self):
        for template in self:
            codes = {
                variant._l10n_pe_ple_existence_code()
                for variant in template.product_variant_ids
            }
            catalogue = template.l10n_pe_existence_catalogue or '9'
            if len(codes) > 1:
                template.l10n_pe_ple_existence_code = self.env._('Varies by variant')
            elif not codes or not next(iter(codes)):
                template.l10n_pe_ple_existence_code = self.env._(
                    'No code - SUNAT rejects the file')
            else:
                template.l10n_pe_ple_existence_code = self.env._(
                    '%(code)s - catalogue %(catalogue)s',
                    code=next(iter(codes)), catalogue=catalogue)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _l10n_pe_ple_existence_code(self):
        """Field 7 of the PLE books for this variant, from the configured source.

        No silent fallback to another source: an empty code is reported by the
        audit and rejected by SUNAT, which is the intended outcome.
        """
        self.ensure_one()
        template = self.product_tmpl_id
        source = template.l10n_pe_existence_code_source or 'internal_reference'
        raw = {
            'internal_reference': self.default_code,
            'barcode': self.barcode,
            'unspsc': template.unspsc_code_id.code,
        }.get(source) or ''
        return EXISTENCE_CODE_SCRUB.sub('', raw)[:24]
