# -*- coding: utf-8 -*-
# Part of Ganemo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.website_appointment.controllers.appointment import WebsiteAppointment


class WebsiteAppointmentSeoFix(WebsiteAppointment):
    """Override _prepare_appointments_cards_data to strip 'domain' from pager URL args.

    Root cause of the crawler trap:
    The native implementation calls website.pager(url_args=kwargs) where kwargs
    contains a 'domain' key built by _appointments_base_domain(). This domain
    includes dynamic Python datetime values (e.g. datetime.datetime(2026,3,13,...))
    that change on every request, causing the pager to generate unique pagination
    hrefs like:
        /appointment/page/2?domain=('end_datetime','>=',datetime.datetime(2026,3,13,5,57,...))

    Each bot crawl of /appointment discovers new pagination links with new datetime
    values, creating an infinite supply of unique URLs that exhaust Odoo workers.

    The fix:
    Call super() to correctly compute results and slice appointment_types by page,
    then replace only the 'pager' dict with a clean version whose url_args omits
    'domain'. The ORM query is unaffected — filtering still works correctly.
    HTML pagination links become clean (/appointment/page/2) or carry only
    legitimate user-facing filters (search, invite_token, filter_appointment_type_ids).
    """

    def _prepare_appointments_cards_data(self, page, appointment_types, **kwargs):
        # Let the parent compute everything correctly (ORM slicing, counts, etc.)
        result = super()._prepare_appointments_cards_data(page, appointment_types, **kwargs)

        # Rebuild the pager with a clean url_args dict that excludes 'domain'.
        # Legitimate user-visible filters (search, invite_token, filter_*) are kept.
        APPOINTMENTS_PER_PAGE = 12
        url_args_clean = {k: v for k, v in kwargs.items() if k != 'domain'}
        pager_clean = request.website.pager(
            url='/appointment',
            url_args=url_args_clean,
            total=result['search_count'],
            page=page,
            step=APPOINTMENTS_PER_PAGE,
            scope=5,
        )
        result['pager'] = pager_clean
        return result
