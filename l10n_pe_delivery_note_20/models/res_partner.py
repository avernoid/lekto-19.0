from odoo import models
from collections import defaultdict


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_structured_address(self):
        self.ensure_one()
        address = "{}, {}, {}, {}, {}".format(
            self.street or '', self.l10n_pe_district.name or '', self.city_id.name or '', self.state_id.name or '', self.country_id.name or '')
        return address

    def get_address_format_report(self):
        address_format = self._get_address_format()
        args = defaultdict(str, {
            'city': self.city_id.name or '',
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_name': self._get_country_name()
        })
        return address_format % args
